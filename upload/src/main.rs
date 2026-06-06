use axum::{
    Router,
    body::Body,
    extract::Extension,
    http::StatusCode,
    response::Html,
    routing::{get, get_service, post},
};
use futures_util::StreamExt;
use multer::Multipart;
use sanitize_filename::sanitize;
use std::{net::SocketAddr, path::PathBuf, sync::Arc};
use tokio::fs::File;
use tokio::io::AsyncWriteExt;
use tower_http::services::ServeDir;

#[derive(Clone)]
struct AppState {
    web_dir: PathBuf,
    static_dir: PathBuf,
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let web_dir = std::env::var("WEB_DIR").unwrap_or_else(|_| "./static/uploads".to_string());
    let static_dir = std::env::var("STATIC_DIR").unwrap_or_else(|_| "./static".to_string());

    let state = Arc::new(AppState {
        web_dir: PathBuf::from(web_dir),
        static_dir: PathBuf::from(static_dir),
    });

    let static_svc = get_service(ServeDir::new(state.static_dir.clone())).handle_error(
        |_err: std::io::Error| async move {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                "Static file error".to_string(),
            )
        },
    );

    let files_svc = get_service(ServeDir::new(state.web_dir.clone())).handle_error(
        |_err: std::io::Error| async move {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                "File serve error".to_string(),
            )
        },
    );

    let app = Router::new()
        .route("/upload", post(handle_upload))
        .route("/", get(handle_index))
        .route_service("/static/*file", static_svc)
        .route_service("/files/*file", files_svc)
        .layer(Extension(state));

    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    tracing::info!("listening on http://{}", addr);
    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}

async fn handle_index(Extension(state): Extension<Arc<AppState>>) -> impl Into<Html<String>> {
    let index_path = state.static_dir.join("index.html");
    match tokio::fs::read_to_string(index_path).await {
        Ok(s) => Html(s),
        Err(_) => Html("<h1>Index not found</h1>".to_string()),
    }
}

async fn handle_upload(
    mut req: axum::http::Request<Body>,
    Extension(state): Extension<Arc<AppState>>,
) -> (StatusCode, String) {
    let headers = req.headers().clone();
    let body = req.into_body();

    let mut multipart = Multipart::new(headers, body);

    let mut saved = Vec::new();

    // ensure directory exists
    if let Err(e) = tokio::fs::create_dir_all(&state.web_dir).await {
        tracing::error!("failed to create web dir: {}", e);
        return (
            StatusCode::INTERNAL_SERVER_ERROR,
            "failed to create upload dir".to_string(),
        );
    }

    while let Some(field) = match multipart.next_field().await {
        Ok(f) => f,
        Err(e) => {
            tracing::error!("multipart error: {}", e);
            return (StatusCode::BAD_REQUEST, format!("multipart error: {}", e));
        }
    } {
        let file_name = field
            .file_name()
            .map(|s| s.to_string())
            .unwrap_or_else(|| "file".to_string());
        let file_name = sanitize(&file_name);
        let data = match field.bytes().await {
            Ok(b) => b,
            Err(e) => {
                tracing::error!("read field bytes: {}", e);
                return (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    format!("read error: {}", e),
                );
            }
        };

        let dest = state.web_dir.join(&file_name);
        match File::create(&dest).await {
            Ok(mut f) => {
                if let Err(e) = f.write_all(&data).await {
                    tracing::error!("write file: {}", e);
                    return (
                        StatusCode::INTERNAL_SERVER_ERROR,
                        format!("write error: {}", e),
                    );
                }
                saved.push(file_name);
            }
            Err(e) => {
                tracing::error!("create file: {}", e);
                return (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    format!("create file error: {}", e),
                );
            }
        }
    }

    (StatusCode::OK, format!("saved: {}", saved.join(", ")))
}
