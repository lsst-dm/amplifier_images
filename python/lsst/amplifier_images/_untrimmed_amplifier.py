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

__all__ = ("UntrimmedAmplifier",)

from typing import TypeVar

from lsst.geom import Box2I

from ._image_section import ImageSection, ImageSectionTransform
from ._amplifier import Amplifier
from ._trimmed_amplifier import TrimmedAmplifier

_T = TypeVar("_T")
_U = TypeVar("_U")


class UntrimmedAmplifier(Amplifier[_T]):
    """An amplifier image that includes overscan regions.

    Parameters
    ----------
    full : `ImageSection`
        Bounding box and optional image for the full untrimmed amplifier.
    amplifier_id : `int`
        Integer ID for this amplifier.
    readout_transform : `ImageSectionTransform`
        Tranform that maps this amplifier into readout coordinates.
    data_bbox : `Box2I`
        Bounding box of the data section in this object's coordinate system.
    data_physical_bbox : `Box2I`
        Bounding box of the data section in the physical (assembled, trimmed)
        coordinate system.
    horizontal_overscan_bbox : `Box2I`
        Bounding box of the horizontal overscan region, in the new object's
        coordinate system.
    vertical_overscan_bbox : `Box2I`
        Bounding box of the vertical overscan region, in the new object's
        coordinate system.
    horizontal_prescan_bbox : `Box2I`
        Bounding box of the horizontal prescan region, in the new object's
        coordinate system.
    raw_detector_transform : `ImageSectionTransform`
        Tranform that maps this amplifier into raw (untrimmed) detector
        coordinates.
    """

    def __init__(
        self,
        full: ImageSection[_T],
        *,
        amplifier_id: int,
        readout_transform: ImageSectionTransform,
        data_bbox: Box2I,
        data_physical_bbox: Box2I,
        horizontal_overscan_bbox: Box2I,
        vertical_overscan_bbox: Box2I,
        horizontal_prescan_bbox: Box2I,
        raw_detector_transform: ImageSectionTransform,
    ):
        assert readout_transform.input_bbox == full.bbox
        assert raw_detector_transform.input_bbox == full.bbox
        assert full.bbox.contains(data_bbox)
        self._full = full
        self._amplifier_id = amplifier_id
        self._readout_transform = readout_transform
        self._data_bbox = data_bbox
        self._data_physical_bbox = data_physical_bbox
        self._horizontal_overscan_bbox = horizontal_overscan_bbox
        self._vertical_overscan_bbox = vertical_overscan_bbox
        self._horizontal_prescan_bbox = horizontal_prescan_bbox
        self._raw_detector_transform = raw_detector_transform

    def copy(self) -> UntrimmedAmplifier[_T]:
        # Docstring inherited.
        return UntrimmedAmplifier(
            self._full.copy(),
            amplifier_id=self.amplifier_id,
            readout_transform=self._readout_transform,
            data_bbox=self._data_bbox,
            data_physical_bbox=self._data_physical_bbox,
            horizontal_overscan_bbox=self._horizontal_overscan_bbox,
            vertical_overscan_bbox=self._vertical_overscan_bbox,
            horizontal_prescan_bbox=self._horizontal_prescan_bbox,
            raw_detector_transform=self._raw_detector_transform,
        )

    def without_images(self) -> UntrimmedAmplifier[None]:
        # Docstring inherited.
        if self._full.image is None:
            return self  # type: ignore
        return UntrimmedAmplifier(
            self._full.without_image(),
            amplifier_id=self.amplifier_id,
            readout_transform=self._readout_transform,
            data_bbox=self._data_bbox,
            data_physical_bbox=self._data_physical_bbox,
            horizontal_overscan_bbox=self._horizontal_overscan_bbox,
            vertical_overscan_bbox=self._vertical_overscan_bbox,
            horizontal_prescan_bbox=self._horizontal_prescan_bbox,
            raw_detector_transform=self._raw_detector_transform,
        )

    @property
    def amplifier_id(self) -> int:
        # Docstring inherited.
        return self._amplifier_id

    @property
    def data(self) -> ImageSection[_T]:
        # Docstring inherited.
        return self._full.subimage(self._data_bbox)

    @property
    def trimmed_view(self) -> TrimmedAmplifier[_T]:
        # Docstring inherited.
        return TrimmedAmplifier(
            self.data,
            amplifier_id=self.amplifier_id,
            readout_transform=self._readout_transform.for_subimage(self._data_bbox),
            horizontal_overscan_is_at_min=(self.horizontal_overscan_boundary == self._data_bbox.getMinX()),
            vertical_overscan_is_at_min=(self.vertical_overscan_boundary == self._data_bbox.getMinY()),
            horizontal_prescan_is_at_min=(self.horizontal_prescan_boundary == self._data_bbox.getMinX()),
            # Physical coordinates for trimmed amp always has the same
            # orientation as the raw detector coordinates, but with different
            # offsets.
            physical_transform=ImageSectionTransform(
                input_bbox=self._data_bbox,
                output_bbox=self._data_physical_bbox,
                flip_x=self.raw_detector_transform.flip_x,
                flip_y=self.raw_detector_transform.flip_y,
            ),
        )

    @property
    def readout_transform(self) -> ImageSectionTransform:
        # Docstring inherited.
        return self._readout_transform

    def into_readout_coordinates(self, *, allow_view: bool = False) -> UntrimmedAmplifier[_T]:
        # Docstring inherited.
        new_full = self._full.apply_transform(self._readout_transform, allow_view=allow_view)
        return UntrimmedAmplifier(
            new_full,
            amplifier_id=self.amplifier_id,
            readout_transform=ImageSectionTransform.make_identity(new_full.bbox),
            data_bbox=self._readout_transform.for_subimage(self._data_bbox).output_bbox,
            data_physical_bbox=self._data_physical_bbox,
            horizontal_overscan_bbox=self._readout_transform.for_subimage(
                self._horizontal_overscan_bbox
            ).output_bbox,
            vertical_overscan_bbox=self._readout_transform.for_subimage(
                self._vertical_overscan_bbox
            ).output_bbox,
            horizontal_prescan_bbox=self._readout_transform.for_subimage(
                self._horizontal_prescan_bbox
            ).output_bbox,
            raw_detector_transform=self.raw_detector_transform.after(self._readout_transform),
        )

    @property
    def horizontal_overscan_boundary(self) -> int:
        # Docstring inherited.
        if self._horizontal_overscan_bbox.getMaxX() < self._data_bbox.getMinX():
            return self._data_bbox.getMinX()
        else:
            assert self._horizontal_overscan_bbox.getMinX() > self._data_bbox.getMaxX()
            return self._data_bbox.getMaxX()

    @property
    def vertical_overscan_boundary(self) -> int:
        # Docstring inherited.
        if self._vertical_overscan_bbox.getMaxY() < self._data_bbox.getMinY():
            return self._data_bbox.getMinY()
        else:
            assert self._vertical_overscan_bbox.getMinY() > self._data_bbox.getMaxY()
            return self._data_bbox.getMaxY()

    @property
    def horizontal_prescan_boundary(self) -> int:
        # Docstring inherited.
        if self._horizontal_prescan_bbox.getMaxX() < self._data_bbox.getMinX():
            return self._data_bbox.getMinX()
        else:
            assert self._horizontal_prescan_bbox.getMinX() > self._data_bbox.getMaxX()
            return self._data_bbox.getMaxX()

    @property
    def horizontal_overscan(self) -> ImageSection[_T]:
        """The region of this amplifier image that corresponds to the
        horizontal (serial) overscan region.

        Guaranteed to be a view that shares pixels with ``self``.
        """
        return self._full.subimage(self._horizontal_overscan_bbox)

    @property
    def vertical_overscan(self) -> ImageSection[_T]:
        """The region of this amplifier image that corresponds to the
        vertical (parallel) overscan region.

        Guaranteed to be a view that shares pixels with ``self``.
        """
        return self._full.subimage(self._vertical_overscan_bbox)

    @property
    def horizontal_prescan(self) -> ImageSection[_T]:
        """The region of this amplifier image that corresponds to the
        horizontal (serial) prescan region.

        Guaranteed to be a view that shares pixels with ``self``.
        """
        return self._full.subimage(self._horizontal_prescan_bbox)

    @property
    def full(self) -> ImageSection[_T]:
        """The full untrimmed amplifier image (`ImageSection`)."""
        return self._full

    def with_new_full_image(self, image: _U) -> UntrimmedAmplifier[_U]:
        """Return a version of this amplifier with the given full image
        and the same bounding boxes and other metadata.

        Parameters
        ----------
        image
            New image.  If this is of a type that has an embedded bounding box
            or size, these must be consistent with ``self.data.bbox``.

        Returns
        -------
        new : `UntrimmedAmplifier`
            An amplifier with the given full image.

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
        new_full = self._full.with_new_image(image)
        return UntrimmedAmplifier(
            new_full,
            amplifier_id=self.amplifier_id,
            readout_transform=self._readout_transform,
            data_bbox=self._data_bbox,
            data_physical_bbox=self._data_physical_bbox,
            horizontal_overscan_bbox=self._horizontal_overscan_bbox,
            vertical_overscan_bbox=self._vertical_overscan_bbox,
            horizontal_prescan_bbox=self._horizontal_prescan_bbox,
            raw_detector_transform=self._raw_detector_transform,
        )

    @property
    def raw_detector_transform(self) -> ImageSectionTransform:
        """Tranform that maps this amplifier into its location in assembled
        but untrimmed raw detector coordinates (`ImageSectionTransform`).
        """
        return self._raw_detector_transform

    def into_raw_detector_coordinates(self, *, allow_view: bool = False) -> UntrimmedAmplifier[_T]:
        """Return a new `Amplifier` with the same trim state that is guaranteed
        to satisfy ``self.raw_detector_transform.is_identity``.

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
        amplifier : `UntrimmedAmplifer`
            Amplifier in raw detector coordinates.
        """
        new_full = self._full.apply_transform(self.raw_detector_transform, allow_view=allow_view)
        return UntrimmedAmplifier(
            new_full,
            amplifier_id=self.amplifier_id,
            readout_transform=self._readout_transform.after(self.raw_detector_transform),
            data_bbox=self.raw_detector_transform.for_subimage(self._data_bbox).output_bbox,
            data_physical_bbox=self._data_physical_bbox,
            horizontal_overscan_bbox=self.raw_detector_transform.for_subimage(
                self._horizontal_overscan_bbox
            ).output_bbox,
            vertical_overscan_bbox=self.raw_detector_transform.for_subimage(
                self._vertical_overscan_bbox
            ).output_bbox,
            horizontal_prescan_bbox=self.raw_detector_transform.for_subimage(
                self._horizontal_prescan_bbox
            ).output_bbox,
            raw_detector_transform=ImageSectionTransform.make_identity(new_full.bbox),
        )
