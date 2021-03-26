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

__all__ = (
    "AssembledTrimmedAmplifierSet",
    "TrimmedAmplifierSet",
    "UnassembledTrimmedAmplifierSet",
)

from abc import abstractmethod
from typing import Any, Iterable, Iterator, List, TypeVar

from lsst.geom import Box2I

from ._image_section import ImageSection
from ._trimmed_amplifier import TrimmedAmplifier
from ._amplifier_set import AmplifierSet, IncompleteAmplifierSetError

_T = TypeVar("_T")
_U = TypeVar("_U")


class TrimmedAmplifierSet(AmplifierSet[_T]):
    """An `AmplifierSet` whose elements are guaranteed to be trimmed.

    This is an intermediate base that does not implement all abstract methods
    and properties of `AmplifierSet`.

    Parameters
    ----------
    amplifiers : `Iterable` [ `TrimmedAmplifier` ]
        An iterable of `TrimmedAmplifer` objects to include in the set.
        Iterators and single-pass iterators are permitted.  Must be from the
        same detector, and have the same image type.
    observation_info, optional
        Additional information describing an observation that is the same for
        all amplifiers in the detector.  See also
        `AmplifierSet.observation_info`.
    """

    def __init__(
        self,
        amplifiers: Iterable[TrimmedAmplifier[_T]],
        *,
        observation_info: Any = None,
    ):
        self._mapping = {amp.amplifier_id: amp for amp in amplifiers}
        self._observation_info = observation_info

    def __getitem__(self, amplifier_id: int) -> TrimmedAmplifier[_T]:
        return self._mapping[amplifier_id]

    def __iter__(self) -> Iterator[TrimmedAmplifier[_T]]:
        return iter(self._mapping.values())

    def __len__(self) -> int:
        return len(self._mapping)

    @property
    def observation_info(self) -> Any:
        # Docstring inherited.
        return self._observation_info

    @property
    def trimmed_view(self) -> TrimmedAmplifierSet[_T]:
        # Docstring inherited.
        return self

    @abstractmethod
    def copy(self) -> TrimmedAmplifierSet[_T]:
        # Docstring inherited; this method only exists to change the return
        # type (covariantly).
        raise NotImplementedError()

    @abstractmethod
    def without_images(self) -> TrimmedAmplifierSet[None]:
        # Docstring inherited; this method only exists to change the return
        # type (covariantly).
        raise NotImplementedError()


class UnassembledTrimmedAmplifierSet(TrimmedAmplifierSet[_T]):
    """A `TrimmedAmplifierSet` made of separate, single-amplifier images.

    Parameters
    ----------
    amplifiers : `Iterable` [ `TrimmedAmplifier` ]
        An iterable of `TrimmedAmplifer` objects to include in the set.
        Iterators and single-pass iterators are permitted.  Must be from the
        same detector, and have the same image type.
    is_complete : `bool`
        Whether all amplifiers for the detector are included.
    observation_info, optional
        Additional information describing an observation that is the same for
        all amplifiers in the detector.  See also
        `AmplifierSet.observation_info`.
    """

    def __init__(
        self, amplifiers: Iterable[TrimmedAmplifier[_T]], is_complete: bool, *, observation_info: Any = None
    ):
        super().__init__(amplifiers, observation_info=observation_info)
        self._is_complete = is_complete

    def copy(self) -> TrimmedAmplifierSet[_T]:
        # Docstring inherited.
        return UnassembledTrimmedAmplifierSet(
            (amp.copy() for amp in self),
            is_complete=self._is_complete,
            observation_info=self.observation_info,
        )

    def without_images(self) -> TrimmedAmplifierSet[None]:
        # Docstring inherited.
        return UnassembledTrimmedAmplifierSet(
            (amp.without_images() for amp in self),
            is_complete=self._is_complete,
            observation_info=self.observation_info,
        )

    @property
    def is_complete(self) -> bool:
        # Docstring inherited.
        return self._is_complete

    def into_readout_coordinates(self, *, allow_view: bool = False) -> TrimmedAmplifierSet[_T]:
        # Docstring inherited.
        if allow_view and all(amp.readout_transform.is_identity for amp in self):
            return self
        return UnassembledTrimmedAmplifierSet(
            (amp.into_readout_coordinates(allow_view=allow_view) for amp in self),
            is_complete=self._is_complete,
            observation_info=self.observation_info,
        )

    def assemble_into_trimmed(self, *, allow_view: bool = False) -> AssembledTrimmedAmplifierSet[_T]:
        # Docstring inherited.
        if not self.is_complete or not self:
            raise IncompleteAmplifierSetError()
        detector_bbox = Box2I()
        for amp in self:
            detector_bbox.include(amp.physical_transform.output_bbox)
        # amp is guaranteed to be bound because we tested for 'not self' above.
        detector = amp.data.make_empty(detector_bbox)  # type: ignore
        new_amplifiers: List[TrimmedAmplifier[_T]] = []
        for amp in self:
            new_amp = amp.into_physical_coordinates(allow_view=True)
            detector.assign(new_amp.data)
            new_amplifiers.append(new_amp)
        return AssembledTrimmedAmplifierSet(detector, new_amplifiers, observation_info=self.observation_info)


class AssembledTrimmedAmplifierSet(TrimmedAmplifierSet[_T]):
    """A complete set of all trimmed amplifiers for a detector, assembled into
    a single image.

    Nested amplifiers are guaranteed to be in physical coordinates.

    Parameters
    ----------
    detector : `BasicImageSection`
        Full detector bounding box (in physical coordinates, with no overscan
        regions) and possibly the associated image.  This is used for the pixel
        data for all amplifiers; any pixel data in ``amplifiers`` is ignored.
    amplifiers : `Iterable` [ `TrimmedAmplifier` ]
        An iterable of `TrimmedAmplifer` objects to include in the set.
        Iterators and single-pass iterators are permitted.  Must be from the
        same detector and include all amplifiers in that detector.  Need not
        include images, and any images included are ignored in favor of new
        subimages of ``detector`` (use `AmplifierSet.assemble_into_trimmed` to
        create a new detector image from existing amplifier images).  Need not
        be in physical coordinates.
    observation_info, optional
        Additional information describing an observation that is the same for
        all amplifiers in the detector.  See also
        `AmplifierSet.observation_info`.
    """

    def __init__(
        self,
        detector: ImageSection[_T],
        amplifiers: Iterable[TrimmedAmplifier[Any]],
        *,
        observation_info: Any = None,
    ):
        self._detector = detector
        physical_amplifiers = (amp.into_physical_coordinates(allow_view=True) for amp in amplifiers)
        super().__init__(
            (amp.with_new_data_image(detector.subimage(amp.data.bbox).image) for amp in physical_amplifiers),
            observation_info=observation_info,
        )

    @classmethod
    def from_views(
        cls,
        detector: ImageSection[_T],
        amplifiers: Iterable[TrimmedAmplifier[_T]],
        observation_info: Any = None,
    ) -> AssembledTrimmedAmplifierSet[_T]:
        """Construct from a detector image and existing views into it, with no
        checking.

        This method is primarily for internal use, but external code that can
        guarantee that all input detectors are already views of the given
        detector image may use it as well for efficiency.

        Parameters
        ----------
        detector : `ImageSection`
            Bounding box and optional image for the full detector.
        amplifiers : `Iterable` [ `TrimmedAmplifier` ]
            An iterable of `TrimmedAmplifer` objects to include in the set,
            each of which must already be a subimage view into ``detector``.
            Iterators and single-pass iterators are permitted.  Must be from
            the same detector and include all amplifiers in that detector.
            Must already be in physical coordinates.
        observation_info, optional
            Additional information describing an observation that is the same
            for all amplifiers in the detector.  See also
            `AmplifierSet.observation_info`.

        Returns
        -------
        assembled : `AssembledTrimmedAmplifierSet`
            An assembled set of trimmed amplifiers.
        """
        self = cls.__new__(cls)
        self._detector = detector
        TrimmedAmplifierSet[_T].__init__(self, amplifiers, observation_info=observation_info)
        return self

    @property
    def detector(self) -> ImageSection[_T]:
        """The full trimmed detector image (`ImageSection`)."""
        return self._detector

    def copy(self) -> AssembledTrimmedAmplifierSet[_T]:
        # Docstring inherited.
        return AssembledTrimmedAmplifierSet(
            self._detector.copy(),
            self,
            observation_info=self.observation_info,
        )

    def without_images(self) -> AssembledTrimmedAmplifierSet[None]:
        # Docstring inherited.
        if self._detector.image is None:
            return self  # type: ignore
        else:
            return self.from_views(
                self._detector.without_image(),
                (amp.without_images() for amp in self),
                observation_info=self.observation_info,
            )

    @property
    def is_complete(self) -> bool:
        # Docstring inherited.
        return True

    @property
    def trimmed_view(self) -> AssembledTrimmedAmplifierSet[_T]:
        # Docstring inherited; this method only exists to change the return
        # type (covariantly).
        return self

    def assemble_into_trimmed(self, *, allow_view: bool = False) -> AssembledTrimmedAmplifierSet[_T]:
        # Docstring inherited.
        return self if allow_view else self.copy()

    def with_new_detector_image(self, detector: _U) -> AssembledTrimmedAmplifierSet[_U]:
        """Return an `AssembledTrimmedAmplifierSet` with the same bounding box
        and a different detector image.

        Parameters
        ----------
        image
            New image.  If `None`, this should be equivalent to calling
            `without_image`.  If this object is of a type that has a size or
            bounding box embedded in it, they should already be consistent with
            ``self.bbox``.

        Returns
        -------
        new : `AssembledTrimmedAmplifierSet`
            An `AssembledTrimmedAmplifierSet` with the given detector image.

        Raises
        ------
        TypeError
            Raised if the given image is of a type not recognized by this
            object.  All objects should be able to handle at least their own
            type and `None`.
        ValueError
            Raised if the given image's bounding box is not consistent with
            ``self.detector.bbox``.
        """
        if detector is None:
            return self.without_image()  # type: ignore
        else:
            return AssembledTrimmedAmplifierSet(
                self._detector.with_new_image(detector), self, observation_info=self.observation_info
            )
