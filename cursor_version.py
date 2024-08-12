import requests
from bs4 import BeautifulSoup
import re


def get_latest_cursor_versions():
    url = "https://changelog.cursor.sh/"

    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Find the first h2 element for the main version
        latest_version_header = soup.find("h2")
        main_version = None
        if latest_version_header:
            version_match = re.search(r"\d+\.\d+(\.\d+)?", latest_version_header.text)
            if version_match:
                main_version = version_match.group()

        all_versions = re.findall(
            r"\b(\d+\.\d+(\.\d+){0,2}|\d+\.0|\b0\.\d+)\b", soup.get_text()
        )
        all_versions = [
            v[0] for v in all_versions
        ]  # Extract the full match from each tuple
        all_versions = list(set(all_versions))  # Remove duplicates
        print(all_versions)
        main_version_variations = [
            v for v in all_versions if v.startswith(main_version)
        ]
        print(main_version_variations)

        latest_main_variation = max(
            main_version_variations, key=lambda v: [int(x) for x in v.split(".") if x]
        )

        return main_version, latest_main_variation

    except requests.RequestException as e:
        print(f"Error fetching the changelog: {e}")

    return None, None


if __name__ == "__main__":
    main_version, highest_version = get_latest_cursor_versions()
    if main_version:
        print(f"The main Cursor version is: {main_version}")
        if highest_version != main_version:
            print(f"A newer version was found: {highest_version}")
    else:
        print("Unable to retrieve the latest version.")
