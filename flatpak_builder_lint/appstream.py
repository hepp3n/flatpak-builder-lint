import os
import subprocess
from typing import TypedDict, cast

from lxml import etree


class SubprocessResult(TypedDict):
    stdout: str
    stderr: str
    returncode: int


def validate(path: str, *args: str) -> SubprocessResult:
    if not os.path.isfile(path):
        raise FileNotFoundError("AppStream file not found")

    overrides = {
        "all-categories-ignored": "error",
        "category-invalid": "error",
        "cid-desktopapp-is-not-rdns": "error",
        "cid-domain-not-lowercase": "info",
        "cid-has-number-prefix": "error",
        "cid-missing-affiliation-gnome": "error",
        "cid-rdns-contains-hyphen": "error",
        "component-name-too-long": "info",
        "content-rating-missing": "error",
        "description-has-plaintext-url": "info",
        "desktop-app-launchable-omitted": "error",
        "desktop-file-not-found": "error",
        "developer-id-invalid": "info",
        "developer-id-missing": "error",
        "invalid-child-tag-name": "error",
        "metainfo-filename-cid-mismatch": "error",
        "metainfo-legacy-path": "error",
        "metainfo-multiple-components": "error",
        "name-has-dot-suffix": "info",
        "releases-info-missing": "error",
        "summary-too-long": "info",
        "unknown-tag": "error",
        "app-categories-missing": "info",
    }

    overrides_value = ",".join([f"{k}={v}" for k, v in overrides.items()])

    cmd = subprocess.run(
        ["appstreamcli", "validate", f"--override={overrides_value}", *args, path],
        capture_output=True,
        check=False,
    )

    ret: SubprocessResult = {
        "stdout": cmd.stdout.decode("utf-8"),
        "stderr": cmd.stderr.decode("utf-8"),
        "returncode": cmd.returncode,
    }

    return ret


def parse_xml(path: str) -> etree._ElementTree:
    if not (os.path.exists(path) and os.path.isfile(path)):
        raise FileNotFoundError(f"XML file not found: {path}")

    try:
        return etree.parse(path)
    except etree.XMLSyntaxError as e:
        raise RuntimeError(f"XML syntax error in file {path}: {e!s}") from None


def components(path: str) -> list[etree._Element]:
    return cast(list[etree._Element], parse_xml(path).xpath("/components/component"))


def metainfo_components(path: str) -> list[etree._Element]:
    return cast(list[etree._Element], parse_xml(path).xpath("/component"))


def appstream_id(path: str) -> list[str]:
    aps_id: list[str] = parse_xml(path).xpath("//component/id/text()")
    return aps_id


def get_launchable(path: str) -> list[str]:
    launchable: list[str] = parse_xml(path).xpath("//launchable[@type='desktop-id']/text()")
    return launchable


def is_categories_present(path: str) -> bool:
    categories = parse_xml(path).xpath("//categories/category")
    return bool(categories)


def is_developer_name_present(path: str) -> bool:
    tree = parse_xml(path)
    dev = tree.xpath("//developer[@id]/name/text()")
    legacy_dev = tree.xpath("//developer_name/text()")
    return bool(dev or legacy_dev)


def is_project_license_present(path: str) -> bool:
    plicense = parse_xml(path).xpath("//project_license/text()")
    return bool(plicense)


def get_screenshot_images(path: str) -> list[str]:
    img = parse_xml(path).xpath("//screenshots/screenshot/image/text()")
    return list(img)


def component_type(path: str) -> str | None:
    component_type = parse_xml(path).xpath("//component/@type")
    return component_type[0] if component_type else None


def is_valid_component_type(path: str) -> bool:
    return component_type(path) in {
        "addon",
        "console-application",
        "desktop",
        "desktop-application",
        "runtime",
    }


def check_caption(path: str) -> bool:
    exp = "//screenshot[not(caption/text()) or not(caption)]"
    return not any(e is not None for e in parse_xml(path).xpath(exp))


def get_manifest_key(path: str) -> list[str]:
    tree = parse_xml(path)
    custom: list[str] = tree.xpath("//custom/value[@key='flathub::manifest']/text()")
    metadata: list[str] = tree.xpath("//metadata/value[@key='flathub::manifest']/text()")
    return custom + metadata


def has_icon_key(path: str) -> bool:
    return bool(parse_xml(path).xpath("//icon"))


def icon_no_type(path: str) -> bool:
    return bool(parse_xml(path).xpath("//icon[not(@type)]"))


def is_remote_icon_mirrored(path: str) -> bool:
    remote_icons = parse_xml(path).xpath("//icon[@type='remote']/text()")
    return all(icon.startswith("https://dl.flathub.org/media/") for icon in remote_icons)


def get_icon_filename(path: str) -> str | None:
    if icons := parse_xml(path).xpath("//icon[@type='cached']"):
        return str(icons[0].text)
    return None


def all_release_has_timestamp(path: str) -> bool:
    return not parse_xml(path).xpath("//releases/release[not(@timestamp)]")
