# This file is part of amplifier_images.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

__all__ = ("AmplifierSet",)

from abc import abstractmethod
from typing import Any, Generic, Iterator, TypeVar, TYPE_CHECKING

from ._amplifier import Amplifier

if TYPE_CHECKING:
    from ._trimmed_amplifier_sets import (
        AssembledTrimmedAmplifierSet,
        TrimmedAmplifierSet,
    )

_T = TypeVar("_T")


class IncompleteAmplifierSetError(RuntimeError):
    """Exception raised when attempting to assemble an `AmplifierSet` for which
    `AmplifierSet.is_complete` is `False`.
    """

    def __init__(self) -> None:
        super().__init__(
            "Cannot assemble an amplifier set unless all amplifiers in the detector are present."
        )


class AmplifierSet(Generic[_T]):
    """A container for amplifiers.

    Notes
    -----
    This is not guaranteed to include all amplifiers for a detector, but it can
    only hold amplifiers that are from the same detector.  It makes no
    guarantees about trim state or orientation (its subclasses generally do).
    """

    @abstractmethod
    def __getitem__(self, amplifier_id: int) -> Amplifier[_T]:
        raise NotImplementedError()

    @abstractmethod
    def __iter__(self) -> Iterator[Amplifier[_T]]:
        raise NotImplementedError()

    @abstractmethod
    def __len__(self) -> int:
        raise NotImplementedError()

    @property
    @abstractmethod
    def observation_info(self) -> Any:
        """Additional information describing an observation that is the same
        for all amplifiers in a detector.

        The type of this attribute is unspecified as it is simply passed
        through as a black box through various `AmplifierSet` methods (e.g.
        assembly).  The ``astro_metadata_translator`` package's
        `ObservationInfo` is a natural candidate, and the inspiration for the
        name.
        """
        raise NotImplementedError()

    @abstractmethod
    def copy(self) -> AmplifierSet[_T]:
        """Return a deep copy of this set."""
        raise NotImplementedError()

    @abstractmethod
    def without_images(self) -> AmplifierSet[None]:
        """Return an equivalent `AmplifierSet` with no image data (just
        bounding boxes and metadata).
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def is_complete(self) -> bool:
        """`True` if this set contains all amplifiers for a single detector,
        and `False` otherwise.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def trimmed_view(self) -> TrimmedAmplifierSet[_T]:
        """Return a new set of amplifiers that contain only data sections.

        The returned amplifiers are guaranteed to share pixels with those in
        ``self``, but if ``self`` is assembled, the returned amplifier set
        may or may not be.
        """
        raise NotImplementedError()

    @abstractmethod
    def into_readout_coordinates(self, *, allow_view: bool = False) -> AmplifierSet[_T]:
        """Return a new `AmplifierSet` with the same trim state whose elements
        are guaranteed to satisfy ``readout_transform.is_identity``.

        Parameters
        ----------
        allow_view : `bool`,
            If `True` (`False` is default), permit the result to share pixels
            with ``self``; in this case it may even be ``self``.  This is
            disabled by default because a copy is required in the general case
            that flips are necessary, so code that implicitly assumes a view is
            returned probably isn't instrument-generic.

        Returns
        -------
        amplifiers : `AmplifierSet`
            An amplifer set whose elements are in readout coordinates.  This
            may not be assembled, even if ``self`` is.
        """
        raise NotImplementedError()

    @abstractmethod
    def assemble_into_trimmed(self, *, allow_view: bool = False) -> AssembledTrimmedAmplifierSet[_T]:
        """Assemble these amplifiers into a single trimmed image.

        Parameters
        ----------
        allow_view : `bool`,
            If `True` (`False` is default), permit the result to share pixels
            with ``self``; in this case it may even be ``self``.  This is
            disabled by default because a copy is required in the general case,
            so code that implicitly assumes a (partial) view is returned
            probably isn't instrument-generic.

        Returns
        -------
        amplifiers : `AssembledTrimmedAmplifierSet`
            An assembled amplifer set.

        Raises
        ------
        IncompleteAmplifierSetError
            Raised if `is_complete` is `False`.
        """
        raise NotImplementedError()
