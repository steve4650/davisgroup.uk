Upload server

Run locally:

```bash
cd upload
cargo run
```

By default the server listens on `127.0.0.1:3000` and serves the static page at `/`.
Uploaded files are saved under `./static/uploads` (change with `WEB_DIR` env var).

Open http://127.0.0.1:3000/ to use the drag-and-drop uploader.
