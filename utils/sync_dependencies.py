#!/usr/bin/env python
import argparse
import pathlib
import typing

import distutils


def extract_setup_requires(setup_path: pathlib.Path) -> typing.Set[str]:
    with setup_path.open('r', encoding='utf-8-sig') as setup:
        content = setup.read()

    try:
        # Super evil `exec` usage. Long story short never run this function on anything ever
        exec(content, globals(), locals()) # pylint: disable=exec-used
    except SystemExit:
        pass

    return set(distutils.core._setup_distribution.install_requires) # pylint: disable


def extract_txt_requires(requirements_path: pathlib.Path) -> typing.Set[str]:
    with requirements_path.open('r', encoding='utf-8-sig') as req:
        requirements = set(line.rstrip('\n') for line in req.readlines())
        requirements.discard('-e .')
        return requirements


def are_syncd(*paths: pathlib.Path) -> bool:
    '''Verifies that dependencies in the `paths` are synced
    '''
    reqs = iter(
        [extract_setup_requires(path) if path.suffix == '.py' else extract_txt_requires(path) for path in paths]
    )
    first = next(reqs, None)
    return all(first == other for other in reqs)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', type=str, nargs='+')
    args = parser.parse_args()
    if not are_syncd(*[pathlib.Path(path) for path in args.path]):
        exit(1)
