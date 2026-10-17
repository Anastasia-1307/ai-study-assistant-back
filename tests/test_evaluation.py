
import json
from pathlib import Path

import requests


BASE_URL = "http://127.0.0.1:8000"
DOCUMENT_ID = "835257ff-90c0-449a-a768-55e3a4001dd3"
DATASET_PATH = Path(__file__).with_name("decorator_dataset.json")


def main():
    with open(DATASET_PATH, "r", encoding="utf-8") as file:
        dataset = json.load(file)

    questions = dataset["questions"]

    print(f"Număr de întrebări: {len(questions)}\n")

    for item in questions:
        question = item["question"]
        expected_answer = item["answer"]

        print("=" * 80)
        print(f"Întrebare {item['id']}: {question}")

        try:
            response = requests.post(
                f"{BASE_URL}/generate-material",
                json={"text": question,
                 "document_id": DOCUMENT_ID
                 },
                timeout=180,
            )

            if response.status_code != 200:
                print(f"Eroare HTTP: {response.status_code}")
                print(response.text)
                continue

            result = response.json().get("result", "")

            print(f"\nRăspunsul modelului:\n{result}")
            print(f"\nRăspuns de referință:\n{expected_answer}")

        except requests.RequestException as error:
            print(f"Eroare de conectare: {error}")

    print("\nEvaluarea s-a încheiat.")


if __name__ == "__main__":
    main()
