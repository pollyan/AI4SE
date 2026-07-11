# sys.path is already set up to include the current directory (tools/intent-tester)
# which allows 'import backend' to work.

from backend.app import run_direct_main

if __name__ == '__main__':
    print("Starting Flask app on port 5002...")
    run_direct_main(port=5002)
