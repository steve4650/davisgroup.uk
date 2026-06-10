import redis

def main():
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    r.set('foo', 'bar')
    print(r.get('foo'))


if __name__ == "__main__":
    main()
