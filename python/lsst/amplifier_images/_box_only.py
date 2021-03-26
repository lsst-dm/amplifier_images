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

__all__ = ("BoxOnlyImageSection",)


from lsst.geom import Box2I

from ._image_section import ImageSection, ImageSectionTransform


class BoxOnlyImageSection(ImageSection[None]):
    """An `ImageSection` implementation with no image payload, just a
    bounding box.

    Parameters
    ----------
    bbox : `Box2I`
        Bounding box for this image section.
    """

    def __init__(self, bbox: Box2I):
        self._bbox = bbox

    @property
    def bbox(self) -> Box2I:
        # Docstring inherited.
        return self._bbox

    @property
    def image(self) -> None:
        # Docstring inherited.
        return None

    def copy(self) -> BoxOnlyImageSection:
        # Docstring inherited.
        # Boxes don't need to be copied because they should never be
        # modified anyway.
        return self

    def make_empty(self, bbox: Box2I) -> BoxOnlyImageSection:
        # Docstring inherited.
        return BoxOnlyImageSection(bbox)

    def subimage(self, bbox: Box2I) -> BoxOnlyImageSection:
        # Docstring inherited.
        assert self.bbox.contains(bbox)
        return BoxOnlyImageSection(bbox)

    def assign(self, other: ImageSection[None]) -> None:
        # Docstring inherited.
        assert self.bbox.contains(other.bbox)

    def apply_transform(self, transform: ImageSectionTransform, *, allow_view: bool) -> BoxOnlyImageSection:
        # Docstring inherited.
        assert transform.input_bbox == self._bbox
        return BoxOnlyImageSection(transform.output_bbox)
