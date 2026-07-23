import getpass

from backend.security import hash_password


def main() -> None:
    password = getpass.getpass("Enter owner password: ")
    confirm = getpass.getpass("Confirm owner password: ")

    if password != confirm:
        raise SystemExit("Passwords do not match.")

    print(hash_password(password))


if __name__ == "__main__":
    main()
