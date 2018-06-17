from typing import TYPE_CHECKING

from python_synth.constants import ANALOGUE_MIN, ANALOGUE_MAX
from python_synth.exceptions import SynthValidationError

if TYPE_CHECKING:
    from attr import Attribute  # noqa
    from typing import ANY  # noqa


def validate_analogue(instance, attribute, value):
    # type: (Any, Attribute, int)
    if value < ANALOGUE_MIN or value > ANALOGUE_MAX:
        raise SynthValidationError(
            'analogue values must be between {ANALOGUE_MIN} and {ANALOGUE_MAX}'
            .format(**locals())
        )


def validate_milliseconds(instance, attribute, value):
    # type: (Any, attr.Attribute, int)
    if value < 0:
        raise SynthValidationError('milliseconds must be positive integers')
