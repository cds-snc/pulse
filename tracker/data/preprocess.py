import os
import csv
from data import models


def pull_data(output: str, connection: models.Connection) -> None:
    os.makedirs(output, exist_ok=True)

    domain_path = os.path.join(output, 'domains.csv')
    owner_path = os.path.join(output, 'owners.csv')
    cipher_path = os.path.join(output, 'ciphers.csv')
    algorithm_path = os.path.join(output, 'algorithms.csv')

    with open(domain_path, 'w', newline='', encoding='utf-8') as domain_file, \
         open(owner_path, 'w', newline='', encoding='utf-8') as owner_file, \
         open(cipher_path, 'w', newline='', encoding='utf-8') as cipher_file, \
         open(algorithm_path, 'w', newline='', encoding='utf-8') as algorithm_file:

        owner_writer = csv.DictWriter(
            owner_file,
            fieldnames=['domain', 'filler', 'organization_en', 'organization_fr']
        )
        domain_writer = csv.DictWriter(domain_file, fieldnames=['domain'])
        cipher_writer = csv.DictWriter(cipher_file, fieldnames=['cipher'])
        algorithm_writer = csv.DictWriter(algorithm_file, fieldnames=['algorithm'])
        domain_writer.writeheader()
        owner_writer.writeheader()
        cipher_writer.writeheader()
        algorithm_writer.writeheader()

        for document in connection.owners.all():
            owner_writer.writerow(document)
        for document in connection.input_domains.all():
            domain_writer.writerow(document)
        for document in connection.ciphers.all():
            cipher_writer.writerow(document)
        for document in connection.algorithms.all():
            algorithm_writer.writerow(document)
