# Maintainer: Cypher <cypher@localhost>
pkgname=dell-g15-fan
pkgver=2.0.0
pkgrel=1
pkgdesc="Industrial-grade hardware fan & thermal control suite for Dell G15 5520 Gaming Laptops on Linux"
arch=('any')
url="https://github.com/cypher-21/DELL_G15_5520_FAN_CONTROL"
license=('MIT')
depends=('python' 'python-pyqt6' 'python-psutil' 'libnotify')
optdepends=('power-profiles-daemon: Dynamic platform profile backend integration')
source=("$pkgname-$pkgver.tar.gz::$url/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('SKIP')

package() {
    cd "$srcdir"
    
    # Python source library
    install -dm755 "$pkgdir/usr/lib/$pkgname"
    install -m755 main.py "$pkgdir/usr/lib/$pkgname/main.py"
    install -m644 dell_fan_backend.py "$pkgdir/usr/lib/$pkgname/dell_fan_backend.py"
    install -m644 dell_g15_fan_gui.py "$pkgdir/usr/lib/$pkgname/dell_g15_fan_gui.py"
    install -m755 dell_g15_fan_cli.py "$pkgdir/usr/lib/$pkgname/dell_g15_fan_cli.py"
    install -m644 fan_curve_engine.py "$pkgdir/usr/lib/$pkgname/fan_curve_engine.py"

    # Executable symlink
    install -dm755 "$pkgdir/usr/bin"
    ln -sf "/usr/lib/$pkgname/main.py" "$pkgdir/usr/bin/$pkgname"

    # Desktop entry & Icon
    install -Dm644 dell-g15-fan.desktop "$pkgdir/usr/share/applications/$pkgname.desktop"
    if [ -f "assets/icon.png" ]; then
        install -Dm644 assets/icon.png "$pkgdir/usr/share/icons/hicolor/256x256/apps/$pkgname.png"
    fi

    # Systemd user unit
    install -Dm644 dell-g15-fan.service "$pkgdir/usr/lib/systemd/user/$pkgname.service"

    # License & Documentation
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
    install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
}
