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
    "AfwImageLike",
    "AfwImageSection",
)

from typing import Optional, Protocol, TypeVar

from lsst.geom import Box2I, PointI

from ._image_section import (
    ImageSection,
    ImageSectionTransform,
)


_S = TypeVar("_S")


class AfwImageLike(Protocol):
    """An interface definition for the afw.image-like objects this module
    provides an `ImageSection` implementation for.

    This simply provides a bit of static type checking by declaring the common
    interface of `lsst.afw.image.Image` and `lsst.afw.image.MaskedImage` that
    we care about here.  It isn't quite complete, as we also use
    `lsst.afw.math.flipImage`, and that isn't a method.
    """

    def __init__(
        self: _S, image: Optional[_S] = None, *, bbox: Optional[Box2I] = None, deep: bool = False
    ) -> _S:
        raise NotImplementedError()

    def getBBox(self) -> Box2I:
        raise NotImplementedError()

    def setXY0(self, point: PointI) -> None:
        raise NotImplementedError()

    def assign(self: _S, other: Optional[_S] = None, *, bbox: Optional[Box2I] = None) -> None:
        raise NotImplementedError()


_V = TypeVar("_V", bound=AfwImageLike)


class AfwImageSection(ImageSection[_V]):
    """An implementation of `ImageSection` that adapts an `lsst.afw.image`
    object.

    Parameters
    ----------
    image : `lsst.afw.image.Image` or `lsst.afw.image.MaskedImage`
        Image to adapt.
    """

    def __init__(self, image: _V):
        self._image = image

    @property
    def bbox(self) -> Box2I:
        # Docstring inherited.
        return self._image.getBBox()

    @property
    def image(self) -> _V:
        # Docstring inherited.
        return self._image

    def copy(self) -> AfwImageSection[_V]:
        # Docstring inherited.
        return AfwImageSection(type(self._image)(self._image, deep=True))

    def make_empty(self, bbox: Box2I) -> AfwImageSection[_V]:
        # Docstring inherited.
        return AfwImageSection(type(self._image)(bbox=bbox))

    def subimage(self, bbox: Box2I) -> AfwImageSection[_V]:
        # Docstring inherited.
        return AfwImageSection(type(self._image)(self._image, bbox=bbox))

    def assign(self, other: ImageSection[_V]) -> None:
        # Docstring inherited.
        self._image.assign(other.image, bbox=other.bbox)

    def apply_transform(self, transform: ImageSectionTransform, *, allow_view: bool) -> AfwImageSection[_V]:
        # Docstring inherited.
        if not (transform.flip_x or transform.flip_y):
            image = type(self._image)(self._image, deep=not allow_view)
        else:
            from lsst.afw.math import flipImage  # type: ignore

            image: AfwImageLike = flipImage(self._image, transform.flip_x, transform.flip_y)
        image.setXY0(transform.output_bbox.getMin())
        return AfwImageSection(image)
