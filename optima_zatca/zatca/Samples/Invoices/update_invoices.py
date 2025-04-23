import json
import os

def update_key_value(data, target_key, new_value):
    """
    Recursively search for a target key in a nested JSON structure and update its value.

    :param data: The JSON object (dict or list) to search.
    :param target_key: The key to search for.
    :param new_value: The value to replace the target key's value with.
    :return: The updated JSON object.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if key == target_key:
                data[key] = new_value  # Update the value if the key matches
            else:
                data[key] = update_key_value(value, target_key, new_value)  # Recurse for nested values
    elif isinstance(data, list):
        for i in range(len(data)):
            data[i] = update_key_value(data[i], target_key, new_value)
    return data


def main():
    """
    Main function to prompt the user for inputs and update a key's value in a JSON file.
    """
    # Prompt the user for inputs
    file_path = input("Enter the full path to the JSON file: ").strip()
    target_key = input("Enter the key to update: ").strip()
    new_value = input("Enter the new value: ").strip()

    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            print(f"Error: The file '{file_path}' does not exist.")
            return

        # Read the JSON file
        with open(file_path, "r") as file:
            json_data = json.load(file)

        # Update the key's value in the JSON data
        updated_data = update_key_value(json_data, target_key, new_value)

        # Overwrite the same file with the updated JSON data
        with open(file_path, "w") as file:
            json.dump(updated_data, file, indent=4)

        print(f"Successfully updated the key '{target_key}' in the file '{file_path}'.")
    
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON. Please check the file format.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()