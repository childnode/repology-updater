# Copyright (C) 2021 Dmitry Marakasov <amdmi3@amdmi3.ru>
#
# This file is part of repology
#
# repology is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# repology is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with repology.  If not, see <http://www.gnu.org/licenses/>.

import pytest

from repology.package import PackageFlags as Pf
from repology.parsers.versions import parse_rpm_version


def test_basic() -> None:
    assert parse_rpm_version([], '1.2.3', '1') == ('1.2.3', 0)


def test_release_starts_with_zero() -> None:
    # Release starts with zero - potentially prerelease or a snapshot
    assert parse_rpm_version([], '1.2.3', '0') == ('1.2.3', Pf.IGNORE)


def test_release_suggests_snapshot() -> None:
    # Release suggests snapshot, even if it doesn't start with zero
    assert parse_rpm_version([], '1.2.3', '1.20200101') == ('1.2.3', Pf.IGNORE)
    assert parse_rpm_version([], '1.2.3', '1.garbage') == ('1.2.3', Pf.IGNORE)


prerelease_params = (
    'suffix,expected_suffix',
    [
        ('alpha1', '-alpha1'),
        ('beta1', '-beta1'),
        ('rc1', '-rc1'),
        ('pre1', '-pre1'),
        ('.alpha1', '-alpha1'),
        ('.beta1', '-beta1'),
        ('.rc1', '-rc1'),
        ('.pre1', '-pre1'),
    ],
)


@pytest.mark.parametrize(*prerelease_params)
def test_release_contains_good_prerelease(suffix, expected_suffix) -> None:
    assert parse_rpm_version([], '1.2.3', f'1{suffix}') == (f'1.2.3{expected_suffix}', Pf.DEVEL)


@pytest.mark.parametrize(*prerelease_params)
def test_release_contains_good_prerelease_and_starts_with_zero(suffix, expected_suffix) -> None:
    assert parse_rpm_version([], '1.2.3', f'0{suffix}') == (f'1.2.3{expected_suffix}', Pf.DEVEL)


@pytest.mark.xfail(reason='not implemented yet, prone to false positives')
def test_release_contains_good_prerelease_dot_separated() -> None:
    assert parse_rpm_version([], '1.2.3', '1.alpha.1') == ('1.2.3-alpha.1', 0)
    assert parse_rpm_version([], '1.2.3', '1.beta.1') == ('1.2.3-beta.1', 0)
    assert parse_rpm_version([], '1.2.3', '1.pre.1') == ('1.2.3-pre.1', 0)

    assert parse_rpm_version([], '1.2.3', '1alpha.1') == ('1.2.3-alpha.1', 0)
    assert parse_rpm_version([], '1.2.3', '1beta.1') == ('1.2.3-beta.1', 0)
    assert parse_rpm_version([], '1.2.3', '1pre.1') == ('1.2.3-pre.1', 0)


def test_release_tag() -> None:
    # Release tags, if specified for the repo, are not condidered as
    # a sing of a snapshot and do not produce IGNORE flag
    assert parse_rpm_version(['el'], '1.2.3', '1.el6') == ('1.2.3', 0)
    assert parse_rpm_version(['el'], '1.2.3', '1.6el') == ('1.2.3', 0)


def test_release_multi() -> None:
    assert parse_rpm_version(['mga'], '1.2.3', '1.mga1.mga2') == ('1.2.3', 0)


def test_release_tag_glued() -> None:
    # Removed tags should not corrupt prerelease versions
    assert parse_rpm_version(['el'], '1.2.3', '1beta3el6') == ('1.2.3-beta3', Pf.DEVEL)


@pytest.mark.parametrize(
    'tags,version,release,expected_version,expected_flags',
    [
        pytest.param(['fc'], '1.5.0', '0.2.alpha.13.fc26', '1.5.0-alpha.13', 0, id='asciidoctor', marks=pytest.mark.xfail(reason='not implemented')),
        pytest.param(['mga'], '1.5', '0.beta.2.mga8', '1.5-beta.2', 0, id='roundcube', marks=pytest.mark.xfail(reason='not implemented')),
        pytest.param(['fc'], '0.2.2', '0.36.beta2.fc29', '0.2.2-beta2', Pf.DEVEL, id='aeskulap'),

        # arguable: we parse out devel suffix from Release, but set IGNORE flag
        # because Release also contains signs of snapshot; instead, we could ignore
        # the latter and consider that the version with prerelease suffix is precise
        # enough to not be a pre-snapshot
        pytest.param(['mga'], '2.1.0', '0.rc9.20190320.7.mga7', '2.1.0-rc9', Pf.IGNORE | Pf.DEVEL, id='kumir'),
        pytest.param(['el'], '1.1.0', '0.4.rc1.git.ff7641193a.el6', '1.1.0-rc1', Pf.IGNORE | Pf.DEVEL, id='novacom-client'),

        # arguable: we parse out pre6, but we don't expect it to be pre6a so we also ignore it
        pytest.param(['mga'], '1.0', '1.0-0.pre6a.8.mga8', '1.0-pre6', Pf.IGNORE | Pf.DEVEL, id='airstrike'),
    ]
)
def test_real_world(tags, version, release, expected_version, expected_flags):
    assert parse_rpm_version(tags, version, release) == (expected_version, expected_flags)
