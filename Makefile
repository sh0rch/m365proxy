PACKAGE=m365proxy
VERSION=2.0.0
BUILD_DIR=build/$(PACKAGE)_$(VERSION)

all: deb

deb:
	@echo "[INFO] Creating DEB package..."
	mkdir -p $(BUILD_DIR)/DEBIAN
	cp m365proxy-debian-control $(BUILD_DIR)/DEBIAN/control
	chmod 755 $(BUILD_DIR)/DEBIAN

	mkdir -p $(BUILD_DIR)/usr/local/bin
	cp install.sh uninstall.sh $(BUILD_DIR)/usr/local/bin/
	chmod +x $(BUILD_DIR)/usr/local/bin/*

	dpkg-deb --build $(BUILD_DIR)
	@echo "[DONE] Package created: $(BUILD_DIR).deb"

clean:
	rm -rf build

.PHONY: all deb clean
