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

__all__ = ("Amplifier",)

from abc import abstractmethod

from typing import Generic, TypeVar, TYPE_CHECKING

from ._image_section import ImageSection, ImageSectionTransform

if TYPE_CHECKING:
    from ._trimmed_amplifier import TrimmedAmplifier

_T = TypeVar("_T")


class Amplifier(Generic[_T]):
    """An image that corresponds to a single amplifier."""

    @abstractmethod
    def copy(self) -> Amplifier[_T]:
        """Return a deep copy of the amplifier object.

        Returns
        -------
        copy : `Amplifier`
            A copy of ``self``.
        """
        raise NotImplementedError()

    @abstractmethod
    def without_images(self) -> Amplifier[None]:
        """Return a version of this amplifier with no image data, just
        bounding boxes and other metadata.

        Returns
        -------
        variant : `Amplifier`
            An amplifier with no image data.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def amplifier_id(self) -> int:
        """Integer ID for this amplifier (`int`)."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def data(self) -> ImageSection[_T]:
        """Data section for the amplifier (`ImageSection`)."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def trimmed_view(self) -> TrimmedAmplifier[_T]:
        """Return an `Amplifier` view containing just the data section.

        This always returns an object that shares pixels with ``self``.  It
        may be ``self`` if it is already trimmed.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def readout_transform(self) -> ImageSectionTransform:
        """Tranform that maps this amplifier into readout coordinates
        (`ImageSectionTransform`).

        In readout coordinates, rows and columns are always ordered
        consistently with the order in which they are read out, the origin
        of the full untrimmed amplifier image is (0, 0).
        """
        raise NotImplementedError()

    @abstractmethod
    def into_readout_coordinates(self, *, allow_view: bool = False) -> Amplifier[_T]:
        """Return a new `Amplifier` with the same trim state that is guaranteed
        to satisfy ``self.readout_transform.is_identity``.

        Parameters
        ----------
        allow_view : `bool`,
            If `True` (`False` is default), permit the result to share pixels
            with ``self``; in this case it may even be ``self``.  This is
            disabled by default because a copy is required in the general case
            that flips are necessary, so code that implicitly assumes a view is
            returned probably isn't instrument-generic.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def horizontal_overscan_boundary(self) -> int:
        """The x coordinate of the boundary of the data region that is adjacent
        to the horizontal overscan region.

        This is always equal to either ``self.data.bbox.getMinX()`` or
        ``self.data.bbox.getMaxX()``.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def vertical_overscan_boundary(self) -> int:
        """The y coordinate of the boundary of the data region that is adjacent
        to the horizontal overscan region.

        This is always equal to either ``self.data.bbox.getMinY()`` or
        ``self.data.bbox.getMaxY()``.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def horizontal_prescan_boundary(self) -> int:
        """The x coordinate of the boundary of the data region that is adjacent
        to the horizontal prescan region.

        This is always equal to either ``self.data.bbox.getMinX()`` or
        ``self.data.bbox.getMaxX()``.
        """
        raise NotImplementedError()
