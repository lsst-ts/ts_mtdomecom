# This file is part of ts_mtdomecom.
#
# Developed for the Vera C. Rubin Observatory Telescope and Site Systems.
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

import json
import pathlib

from .registry import registry

# TODO OSW-862 Remove all references to the old temperature schema.
json_path = pathlib.Path(__file__).parents[0] / "th_status.json"
with open(json_path) as f:
    lines = "".join(f.readlines())
    registry["ThCS"] = json.loads(lines)

json_path = pathlib.Path(__file__).parents[0] / "th_status_new.json"
with open(json_path) as f:
    lines = "".join(f.readlines())
    registry["ThCS_new"] = json.loads(lines)
