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

__all__ = ("NumPyImageSection",)

import numpy as np

from lsst.geom import Box2I, ExtentI, PointI

from ._image_section import (
    ImageSection,
    ImageSectionTransform,
)


class NumPyImageSection(ImageSection[np.ndarray]):
    """An implementation of `ImageSection` that adapts a `numpy.ndarray`
    object.

    Parameters
    ----------
    array : `numpy.ndarray`
        Array to adapt.  ``array.shape[0]`` is used as the bounding box
        height and ``array.shape[1]`` is used as the bounding box height; any
        number of additional dimensions may be present.
    min : `PointI`
        Minimum point of the image's bounding box.
    """

    def __init__(self, array: np.ndarray, bbox_min: PointI):
        self._array = array
        self._bbox_min = bbox_min

    @property
    def bbox(self) -> Box2I:
        # Docstring inherited.
        return Box2I(self._bbox_min, ExtentI(self._array.shape[1], self._array.shape[0]))

    @property
    def image(self) -> np.ndarray:
        # Docstring inherited.
        return self._array

    def copy(self) -> NumPyImageSection:
        # Docstring inherited.
        return NumPyImageSection(self._array.copy(), self._bbox_min)

    def make_empty(self, bbox: Box2I) -> NumPyImageSection:
        # Docstring inherited.
        return NumPyImageSection(np.zeros_like(self._array), self._bbox_min)

    def subimage(self, bbox: Box2I) -> NumPyImageSection:
        # Docstring inherited.
        start = bbox.getMin() - self._bbox_min
        stop = start + bbox.getSize()
        return NumPyImageSection(
            self._array[start.getY() : stop.getY(), start.getX() : stop.getX(), ...],  # noqa:E203
            bbox,
        )

    def assign(self, other: ImageSection[np.ndarray]) -> None:
        # Docstring inherited.
        self.subimage(other.bbox).image[...] = other.image

    def apply_transform(self, transform: ImageSectionTransform, *, allow_view: bool) -> NumPyImageSection:
        # Docstring inherited.
        array = self._array[:: -1 if transform.flip_y else 1, :: -1 if transform.flip_x else 1]
        if not allow_view:
            array = array.copy()
        return NumPyImageSection(array, transform.output_bbox.getMin())
