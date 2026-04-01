import requests

def chat():
    print("Locus client live. Type \'/exit' to quit.")
    while True:
        userInput = input("u: ").strip()
        if not userInput:
            continue
        if userInput.lower() == '/exit':
            break

        try:
            response = requests.post(
                "http://localhost:8000/chat",
                json={"message": userInput}
            )

            if response.status_code == 200:
                print(f"\nLocus: {response.json()['response']}\n")
            else:
                print(f"Error: {response.status_code}")
        except Exception as e:
            print(f"Failed to connect: {e}")

if __name__ == "__main__":
    chat()
            
