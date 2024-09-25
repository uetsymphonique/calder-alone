import os
import yaml

# Paths to the abilities folder and the adversary file
abilities_folder = 'abilities'
adversary_file = 'adversary.yml'
output_file = 'updated_adversary.yml'


def merge_abilities(abilities_folder):
    """
    Merges all abilities from YAML files located in the abilities_folder.
    Returns a combined list of abilities.
    """
    merged_abilities = []

    # Traverse all subdirectories in the abilities folder
    for root, _, files in os.walk(abilities_folder):
        for file in files:
            if file.endswith('.yml') or file.endswith('.yaml'):
                file_path = os.path.join(root, file)

                # Read each YAML file and extend the merged abilities list
                with open(file_path, 'r', encoding='utf-8') as f:
                    abilities = yaml.safe_load(f)
                    if isinstance(abilities, list):
                        merged_abilities.extend(abilities)

    return merged_abilities


def create_updated_adversary_file(adversary_file, output_file, abilities):
    """
    Creates a new YAML file with the adversary object, adding the merged abilities.
    """
    # Read the existing adversary file
    with open(adversary_file, 'r', encoding='utf-8') as f:
        adversary_data = yaml.safe_load(f)

    # Check if adversary_data is a dictionary
    if not isinstance(adversary_data, dict):
        raise ValueError("The adversary.yml file must contain an adversary object (dictionary).")

    # Add merged abilities to the adversary object
    adversary_data['abilities'] = abilities

    # Write the updated adversary data to the new output file
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.safe_dump(adversary_data, f, allow_unicode=True, sort_keys=False)


if __name__ == "__main__":
    # Step 1: Merge all abilities from the abilities folder
    merged_abilities = merge_abilities(abilities_folder)

    # Step 2: Update the adversary object and create a new file with the updated data
    create_updated_adversary_file(adversary_file, output_file, merged_abilities)

    print(f"New file '{output_file}' created with the updated adversary containing {len(merged_abilities)} abilities.")
