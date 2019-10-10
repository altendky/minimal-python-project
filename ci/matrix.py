# This is used for the CI side without any installation
# standard lib only
#
# nabbed from: https://github.com/altendky/romp/blob/602fe43fda8c491f7799f338eaa4ce28ed96cd74/src/romp/_matrix.py

import argparse
import collections
import itertools
import json
import sys
import uuid


vm_images = collections.OrderedDict((
    ('Linux', 'ubuntu-16.04'),
    ('macOS', 'macOS-10.13'),
    ('Windows', 'vs2017-win2016'),
))


all_platforms = tuple(vm_images.keys())


interpreters = collections.OrderedDict((
    ('CPython', 'CPython'),
    # ('PyPy', 'PyPy'),
))


all_interpreters = tuple(interpreters.keys())


versions = collections.OrderedDict((
    ('CPython', ('3.5', '3.6', '3.7')),
    # ('PyPy', ('3.5',)),
))


all_versions = tuple(sorted(set(
    itertools.chain.from_iterable(versions.values())
)))


architectures = collections.OrderedDict((
    ('x86', 'x86'),
    ('x86_64', 'x64'),
))


all_architectures = tuple(architectures.keys())


urls = collections.OrderedDict((
    (('Linux', 'PyPy', '2.7', 'x86_64'), 'https://bitbucket.org/pypy/pypy/downloads/pypy2.7-v7.0.0-linux64.tar.bz2'),
    (('Linux', 'PyPy', '3.5', 'x86_64'), 'https://bitbucket.org/pypy/pypy/downloads/pypy3.5-v7.0.0-linux64.tar.bz2'),
    (('macOS', 'PyPy', '2.7', 'x86_64'), 'https://bitbucket.org/pypy/pypy/downloads/pypy2.7-v7.0.0-osx64.tar.bz2'),
    (('macOS', 'PyPy', '3.5', 'x86_64'), 'https://bitbucket.org/pypy/pypy/downloads/pypy3.5-v7.0.0-osx64.tar.bz2'),
    (('Windows', 'PyPy', '2.7', 'x86'), 'https://bitbucket.org/pypy/pypy/downloads/pypy2.7-v7.0.0-win32.zip'),
    (('Windows', 'PyPy', '3.5', 'x86'), 'https://bitbucket.org/pypy/pypy/downloads/pypy3.5-v7.0.0-win32.zip'),
))


extracters = {
    'Linux': 'tar -xvf',
    'macOS': 'tar -xvf',
    'Windows': 'unzip',
}


class Environment:
    def __init__(self, platform, interpreter, version, architecture):
        self.platform = platform
        self.vm_image = vm_images[platform]
        self.interpreter = interpreter
        self.version = version
        self.architecture = architecture

    @classmethod
    def from_string(cls, environment_string):
        platform, interpreter, version, architecture = (
            environment_string.split('-')
        )
        return cls(
            platform=platform,
            interpreter=interpreter,
            version=version,
            architecture=architecture,
        )

    def tox_env(self):
        env = 'py'
        if self.interpreter == 'PyPy':
            env += 'py'
            if self.version[0] == '3':
                env += '3'
        else:
            env += self.version.replace('.', '')

        return env

    def matrix_version(self):
        if self.interpreter == 'CPython':
            return self.version

        return 'pypy{}'.format(self.version[0])

    def to_matrix_entry(self):
        entry_uuid = str(uuid.uuid4())

        return (
            '{platform} {interpreter} {version} {architecture}'.format(
                platform=self.platform,
                interpreter=self.interpreter,
                version=self.version,
                architecture=self.architecture,
            ),
            {
                'platform': self.platform,
                'vmImage': self.vm_image,
                'versionSpec': self.matrix_version(),
                'architecture': architectures[self.architecture],
                'python_url': urls.get((
                    self.platform,
                    self.interpreter,
                    self.version,
                    self.architecture,
                ), ''),
                'extracter': extracters[self.platform],
                'TOXENV': self.tox_env(),
                'uuid': entry_uuid,
                'artifacts_archive': 'artifacts.{}.tar.gz'.format(entry_uuid),
            },
        )

    def __eq__(self, other):
        return (
            self.platform == other.platform
            and self.vm_image == other.vm_image
            and self.interpreter == other.interpreter
            and self.version == other.version
            and self.architecture == other.architecture
        )


def build_all_environments():
    return [
        Environment(
            platform=platform,
            interpreter=interpreter,
            version=version,
            architecture=architecture,
        )
        for platform in all_platforms
        for interpreter in all_interpreters
        for version in versions[interpreter]
        for architecture in all_architectures
        if not (
                (
                        architecture == 'x86'
                        and (
                                platform != 'Windows'
                        )
                )
                or (
                        platform == 'Windows'
                        and interpreter == 'PyPy'
                        and architecture == 'x86_64'
                )
        )
    ]


def string_from_environments(environments):
    return '|'.join(
        '-'.join((
            environment.platform,
            environment.interpreter,
            environment.version,
            str(environment.architecture)))
        for environment in environments
    )


def build_environments_from_string(environments):
    environments = [
        Environment.from_string(environment_string=environment)
        for environment in environments.split('|')
    ]

    return collections.OrderedDict(
        environment.to_matrix_entry()
        for environment in environments
    )


def build_environments(
        platforms=all_platforms,
        interpreters=all_interpreters,
        versions=all_versions,
        architectures=all_architectures,
):
    all_environments = build_all_environments()

    built_environments = [
        Environment(
            platform=platform,
            interpreter=interpreter,
            version=version,
            architecture=architecture,
        )
        for platform in platforms
        for interpreter in interpreters
        for version in versions
        for architecture in architectures
    ]

    return [
        environment
        for environment in built_environments
        if environment in all_environments
    ]


def lower(x):
    return [y.lower() for y in x]


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.set_defaults(func=parser.print_help)

    test_environments = [
        environment
        for environment in build_all_environments()
    ]

    # parser.add_argument(
    #     '--environments',
    #     default=string_from_environments(test_environments),
    # )

    parser.add_argument(
        '--platform',
        action='append',
        choices=lower(all_platforms),
        default=[],
        dest='platforms',
    )

    parser.add_argument(
        '--interpreter',
        action='append',
        choices=lower(all_interpreters),
        default=[],
        dest='interpreters',
    )

    parser.add_argument(
        '--version',
        action='append',
        choices=lower(all_versions),
        default=[],
        dest='versions',
    )

    parser.add_argument(
        '--architecture',
        action='append',
        choices=lower(architectures),
        default=[],
        dest='architectures'
    )

    args = parser.parse_args()

    matrix_entries = []

    for environment in build_all_environments():
        if (
                environment.platform.lower() not in args.platforms
                or environment.interpreter.lower() not in args.interpreters
                or environment.version.lower() not in args.versions
                or environment.architecture.lower() not in args.architectures
        ):
            prefix = 'skip'
        else:
            prefix = ''
            matrix_entries.append(environment.to_matrix_entry())

        entry = environment.to_matrix_entry()

        print('{prefix:<5} {entry}'.format(prefix=prefix, entry=entry))

        matrix_entries

    # matrix_entries = build_environments_from_string(
    #     environments=args.environments,
    # )

    json_matrix = json.dumps(matrix_entries)

    command = (
        '##vso[task.setVariable variable=JobsToRun;isOutput=True]'
        + json_matrix
    )

    print(command.lstrip('#'))
    print(json.dumps(matrix_entries, indent=4))
    print(command)


if __name__ == '__main__':
    sys.exit(main())
