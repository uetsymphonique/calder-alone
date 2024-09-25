import os
import yaml
import uuid

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


def update_ids_and_atomic_ordering(adversary_data, abilities):
    """
    Updates the 'id' field of the adversary and each ability in the list with a new UUID.
    Synchronizes the 'atomic_ordering' list with the new ability IDs.
    """
    # Update adversary id
    adversary_data['id'] = str(uuid.uuid4())

    # Create a mapping from old ability ids to new UUIDs
    id_mapping = {}

    # Update each ability's id and store the mapping
    for ability in abilities:
        new_id = str(uuid.uuid4())
        id_mapping[ability['id']] = new_id
        ability['id'] = new_id

    # Synchronize atomic_ordering with new ability ids
    if 'atomic_ordering' in adversary_data:
        adversary_data['atomic_ordering'] = [
            id_mapping.get(old_id, old_id) for old_id in adversary_data['atomic_ordering']
        ]

    return adversary_data, abilities


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

    # Update the ids of the adversary and abilities, and sync atomic_ordering
    adversary_data, updated_abilities = update_ids_and_atomic_ordering(adversary_data, abilities)

    # Add merged abilities to the adversary object
    adversary_data['abilities'] = updated_abilities

    # Write the updated adversary data to the new output file
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.safe_dump(adversary_data, f, allow_unicode=True, sort_keys=False)


if __name__ == "__main__":
    # Step 1: Merge all abilities from the abilities folder
    merged_abilities = merge_abilities(abilities_folder)

    # Step 2: Update the adversary object and create a new file with the updated data
    create_updated_adversary_file(adversary_file, output_file, merged_abilities)

    print(f"New file '{output_file}' created with the updated adversary containing {len(merged_abilities)} abilities.")
