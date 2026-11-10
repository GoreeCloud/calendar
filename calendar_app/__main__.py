"""Run with: python -m calendar_app serve | create-admin --email YOU@example.com"""
import argparse
import getpass
import os
from .core import Failure, create_user, init_database, make_server

def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description="GoreeCloud Calendar self-hosted preview")
    parser.add_argument("--database", default=os.getenv("GC_CALENDAR_DB", "./data/calendar.sqlite3"))
    commands = parser.add_subparsers(dest="command", required=True)
    admin = commands.add_parser("create-admin", help="Create a local user and their private calendar")
    admin.add_argument("--email", required=True)
    serve = commands.add_parser("serve", help="Start the HTTP server")
    serve.add_argument("--host", default=os.getenv("GC_CALENDAR_HOST", "127.0.0.1"))
    serve.add_argument("--port", type=int, default=int(os.getenv("GC_CALENDAR_PORT", "8787")))
    args = parser.parse_args()
    if args.command == "create-admin":
        init_database(args.database)
        password = getpass.getpass("Password (12+ characters): ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            parser.error("Passwords do not match")
        try:
            create_user(args.database, args.email, password)
        except Failure as error:
            parser.error(error.message)
        print("Account created. No password or authentication token was logged.")
    else:
        with make_server(args.database,args.host,args.port) as server:
            print(f"GoreeCloud Calendar listening at http://{args.host}:{server.server_address[1]}")
            print("Local access only by default. Use a properly configured HTTPS reverse proxy for remote access.")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass

if __name__ == "__main__":
    main()
