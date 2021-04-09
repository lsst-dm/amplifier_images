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

__all__ = ("TrimmedAmplifier",)

from typing import TypeVar

from ._amplifier import Amplifier
from ._image_section import ImageSection, ImageSectionTransform

_T = TypeVar("_T")
_U = TypeVar("_U")


class TrimmedAmplifier(Amplifier[_T]):
    """An amplifier image that contains only the data section (no
    overscan regions).

    Parameters
    ----------
    data : `ImageSection`
        Bounding box and optional image for the data section.
    amplifier_id : `int`
        Integer ID for this amplifier.
    readout_transform : `ImageSectionTransform`
        Tranform that maps this amplifier into readout coordinates.
    horizontal_overscan_is_at_min : `bool`
        `True` if the horizontal overscan is on the side of the minimum x
        coordinate of the data bounding box, `False` otherwise.
    vertical_overscan_is_at_min : `bool`
        `True` if the vertical overscan is on the side of the minimum y
        coordinate of the data bounding box, `False` otherwise.
    horizontal_prescan_is_at_min : `bool`
        `True` if the horizontal prescan is on the side of the minimum x
        coordinate of the data bounding box, `False` otherwise.
    physical_transform : `ImageSectionTransform`
        Tranform that maps this amplifier into physical (trimmed detector)
        coordinates.
    """

    def __init__(
        self,
        data: ImageSection[_T],
        *,
        amplifier_id: int,
        readout_transform: ImageSectionTransform,
        horizontal_overscan_is_at_min: bool,
        vertical_overscan_is_at_min: bool,
        horizontal_prescan_is_at_min: bool,
        physical_transform: ImageSectionTransform,
    ):
        assert readout_transform.input_bbox == data.bbox
        assert physical_transform.input_bbox == data.bbox
        self._data = data
        self._amplifier_id = amplifier_id
        self._readout_transform = readout_transform
        self._horizontal_overscan_is_at_min = horizontal_overscan_is_at_min
        self._vertical_overscan_is_at_min = vertical_overscan_is_at_min
        self._horizontal_prescan_is_at_min = horizontal_prescan_is_at_min
        self._physical_transform = physical_transform

    def copy(self) -> TrimmedAmplifier[_T]:
        # Docstring inherited.
        return TrimmedAmplifier(
            self._data.copy(),
            amplifier_id=self.amplifier_id,
            readout_transform=self._readout_transform,
            horizontal_overscan_is_at_min=self._horizontal_overscan_is_at_min,
            vertical_overscan_is_at_min=self._vertical_overscan_is_at_min,
            horizontal_prescan_is_at_min=self._horizontal_prescan_is_at_min,
            physical_transform=self._physical_transform,
        )

    def without_images(self) -> TrimmedAmplifier[None]:
        # Docstring inherited.
        if self._data.image is None:
            return self  # type: ignore
        return TrimmedAmplifier(
            self._data.without_image(),
            amplifier_id=self.amplifier_id,
            readout_transform=self._readout_transform,
            horizontal_overscan_is_at_min=self._horizontal_overscan_is_at_min,
            vertical_overscan_is_at_min=self._vertical_overscan_is_at_min,
            horizontal_prescan_is_at_min=self._horizontal_prescan_is_at_min,
            physical_transform=self._physical_transform,
        )

    @property
    def amplifier_id(self) -> int:
        # Docstring inherited.
        return self._amplifier_id

    @property
    def data(self) -> ImageSection[_T]:
        # Docstring inherited.
        return self._data

    @property
    def trimmed_view(self) -> TrimmedAmplifier[_T]:
        # Docstring inherited.
        return self

    @property
    def readout_transform(self) -> ImageSectionTransform:
        # Docstring inherited.
        return self._readout_transform

    def into_readout_coordinates(self, *, allow_view: bool = False) -> TrimmedAmplifier[_T]:
        # Docstring inherited.
        new_data = self._data.apply_transform(self._readout_transform, allow_view=allow_view)
        return TrimmedAmplifier[_T](
            new_data,
            amplifier_id=self.amplifier_id,
            readout_transform=ImageSectionTransform(new_data.bbox),
            horizontal_overscan_is_at_min=(
                self._horizontal_overscan_is_at_min != self._readout_transform.flip_x
            ),
            vertical_overscan_is_at_min=(self._vertical_overscan_is_at_min != self._readout_transform.flip_y),
            horizontal_prescan_is_at_min=(
                self._horizontal_prescan_is_at_min != self._readout_transform.flip_x
            ),
            physical_transform=self._physical_transform.after(self._readout_transform),
        )

    @property
    def horizontal_overscan_boundary(self) -> int:
        # Docstring inherited.
        return self._data.bbox.getMinX() if self._horizontal_overscan_is_at_min else self._data.bbox.getMaxX()

    @property
    def vertical_overscan_boundary(self) -> int:
        # Docstring inherited.
        return self._data.bbox.getMinY() if self._vertical_overscan_is_at_min else self._data.bbox.getMaxY()

    @property
    def horizontal_prescan_boundary(self) -> int:
        # Docstring inherited.
        return self._data.bbox.getMinX() if self._horizontal_prescan_is_at_min else self._data.bbox.getMaxX()

    def with_new_data_image(self, image: _U) -> TrimmedAmplifier[_U]:
        """Return a version of this amplifier with the given data section image
        and the same bounding boxes and other metadata.

        Parameters
        ----------
        image
            New image.  If this is of a type that has an embedded bounding box
            or size, these must be consistent with ``self.data.bbox``.

        Returns
        -------
        new : `TrimmedAmplifier`
            An amplifier with the given data section image.

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
        new_data = self._data.with_new_image(image)
        return TrimmedAmplifier(
            new_data,
            amplifier_id=self.amplifier_id,
            readout_transform=self._readout_transform,
            horizontal_overscan_is_at_min=self._horizontal_overscan_is_at_min,
            vertical_overscan_is_at_min=self._vertical_overscan_is_at_min,
            horizontal_prescan_is_at_min=self._horizontal_prescan_is_at_min,
            physical_transform=self._physical_transform,
        )

    @property
    def physical_transform(self) -> ImageSectionTransform:
        """Tranform that maps this amplifier into its location in assembled
        and trimmed detector coordinates (`ImageSectionTransform`).
        """
        return self._physical_transform

    def into_physical_coordinates(self, *, allow_view: bool = False) -> TrimmedAmplifier[_T]:
        """Return a new `Amplifier` with the same trim state that is guaranteed
        to satisfy ``self.physical_transform.is_identity``.

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
        amplifier : `TrimmedAmplifer`
            Amplifier in physical coordinates.
        """
        new_data = self._data.apply_transform(self._physical_transform, allow_view=allow_view)
        return TrimmedAmplifier(
            new_data,
            amplifier_id=self.amplifier_id,
            readout_transform=self._readout_transform.after(self._physical_transform),
            horizontal_overscan_is_at_min=(
                self._horizontal_overscan_is_at_min != self._physical_transform.flip_x
            ),
            vertical_overscan_is_at_min=(
                self._vertical_overscan_is_at_min != self._physical_transform.flip_y
            ),
            horizontal_prescan_is_at_min=(
                self._horizontal_prescan_is_at_min != self._physical_transform.flip_x
            ),
            physical_transform=ImageSectionTransform.make_identity(new_data.bbox),
        )
