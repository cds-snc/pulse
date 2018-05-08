import typing

class Domain(typing.NamedTuple):
    domain: str

    def to_dict(self) -> typing.Dict[str, str]:
        return {
            'domain': self.domain
        }

class ParentDomain(Domain):
    organization: str

    def to_dict(self) -> typing.Dict[str, str]:
        return {
            'domain': self.domain,
            'organization': self.organization,
        }
