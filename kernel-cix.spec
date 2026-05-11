# ============================================================================
# Spec file for Cix P1 (Orion O6) custom kernel
# Based on Linux 7.0.4 with Cix ACPI/SoC patches for ARM64 (aarch64)
#
# Build method: Copr Custom "make srpm"
# .copr/Makefile downloads kernel tarball, then rpmbuild -bs creates SRPM.
# Copr then builds the SRPM into binary RPMs on aarch64 builders.
# ============================================================================

# ---- Versioning ----
# Kernel release string format: 7.0.4-1.fc44.aarch64
# EXTRAVERSION passed to make sets the local version suffix
%define rpmver    %{version}-%{release}
%define kverstr   %{rpmver}.%{_arch}

# ---- Package Metadata ----
Name:           kernel-cix
Version:        7.0.4
Release:        1%{?dist}
Summary:        Linux Kernel 7.0.4 with Cix P1 (Orion O6) patches

License:        GPLv2
URL:            https://github.com/HougeLangley/cix-linux-main

# Kernel source tarball (downloaded by .copr/Makefile, or via spectool -g locally)
%define ksource linux-7.0.4
Source0:        https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-7.0.4.tar.xz

# Combined Cix patches + config (created by .copr/Makefile)
Source1:        cix-sources.tar.gz

# Only build for 64-bit ARM
ExclusiveArch:  aarch64

# ---- Build Dependencies ----
BuildRequires:  bash binutils bison coreutils diffutils
BuildRequires:  dwarves elfutils-devel findutils flex gcc git-core
BuildRequires:  gzip hostname kmod m4 make openssl-devel
BuildRequires:  perl-interpreter perl-devel python3-devel rsync tar xz
BuildRequires:  bc

%description
Linux Kernel 7.0.4 with Cix P1 (Orion O6) SoC patches enabling ACPI
support, mailbox, SCMI, clock, reset, GPIO, I2C, USB Type-C, DisplayPort,
HDMI audio, DSP remoteproc, GPU (panthor), and other Cix-specific
hardware drivers on ARM64.

Kernel command line requirements: clk_ignore_unused

%package devel
Summary:        Development files for building external kernel modules
Requires:       %{name} = %{version}-%{release}

%description devel
Kernel headers, Makefiles, and .config required to build external
kernel modules (DKMS, VirtualBox, NVIDIA, etc.) against %{name}.

# ============================================================================
# %%prep - Extract kernel source, apply Cix patches, configure
# ============================================================================

%prep
%setup -q -n %{ksource}

# ---- Extract Cix patches and config from Source1 tarball ----
%setup -q -T -D -n %{ksource} -b 1
# Now patches-7.0/ and config/ are extracted alongside the kernel source

# ---- Apply Cix patches via git am (preserves authorship, handles ordering) ----
git init -q
git config user.email "builder@cix-copr"
git config user.name "Copr Builder"
git add -A
git commit -q -m "%{ksource} base"

echo "=== Applying Cix patches ==="
for patch in ../patches-7.0/*.patch; do
    patch_name=$(basename "$patch")
    echo "  [%{name}] $patch_name"
    git am "$patch" || {
        echo "ERROR: Failed to apply $patch_name"
        echo "--- git am log ---"
        git am --show-current-patch=diff 2>/dev/null | head -80
        exit 1
    }
done

patch_count=$(ls ../patches-7.0/*.patch 2>/dev/null | wc -l)
echo "=== Applied $patch_count Cix patches ==="

# ---- Apply Cix defconfig ----
cp ../config/config-7.0.defconfig .config
make ARCH=arm64 olddefconfig

# ---- Tune config for RPM packaging ----
# Disable CONFIG_LOCALVERSION_AUTO (would append git hash)
scripts/config --undefine CONFIG_LOCALVERSION_AUTO
# Set module compression to reduce package size
scripts/config --enable CONFIG_MODULE_COMPRESS_ZSTD
# Disable signing (handled by rpm build or skipped)
scripts/config --disable CONFIG_MODULE_SIG_ALL
# Ensure IKCONFIG is built-in (so /proc/config.gz works)
scripts/config --enable CONFIG_IKCONFIG
scripts/config --enable CONFIG_IKCONFIG_PROC

make ARCH=arm64 olddefconfig

# ============================================================================
# %%build - Compile kernel image, modules, and device trees
# ============================================================================

%build
export ARCH=arm64

# EXTRAVERSION sets the -release.arch suffix => kernelrelease = 7.0.4-1.fc44.aarch64
# This matches the %%{kverstr} macro exactly
make %{?_smp_mflags} EXTRAVERSION=-%{release}.%{_arch} Image
make %{?_smp_mflags} EXTRAVERSION=-%{release}.%{_arch} modules
make %{?_smp_mflags} EXTRAVERSION=-%{release}.%{_arch} dtbs 2>/dev/null || echo "(no DTS changes)"

# ============================================================================
# %%install - Install to buildroot
# ============================================================================

%install
export ARCH=arm64

# ---- Kernel modules → /lib/modules/<kverstr> ----
make INSTALL_MOD_PATH=%{buildroot} INSTALL_MOD_STRIP=1 \
     EXTRAVERSION=-%{release}.%{_arch} \
     modules_install

# ---- Kernel image → /boot/vmlinuz-<kverstr> ----
# ARM64 uses uncompressed Image (or Image.gz); Fedora ARM uses Image
install -Dm644 arch/arm64/boot/Image %{buildroot}/boot/vmlinuz-%{kverstr}

# ---- System.map ----
install -Dm644 System.map %{buildroot}/boot/System.map-%{kverstr}

# ---- Kernel config ----
install -Dm644 .config %{buildroot}/boot/config-%{kverstr}

# ---- Module symbol versions (for DKMS) ----
install -Dm644 Module.symvers %{buildroot}/boot/symvers-%{kverstr}

# ---- Device tree blobs (if Cix patches produce any) ----
mkdir -p %{buildroot}/boot/dtb-%{kverstr}
if ls arch/arm64/boot/dts/cix/*.dtb >/dev/null 2>&1; then
    install -Dm644 arch/arm64/boot/dts/cix/*.dtb -t %{buildroot}/boot/dtb-%{kverstr}/
fi

# ---- kernel-devel: prepare files for building external modules ----
# (Following Fedora kernel.spec patterns)
DEVEL_ROOT=%{buildroot}/usr/src/kernels/%{kverstr}
mkdir -p "$DEVEL_ROOT"

# Copy build system files
cp -a Makefile "$DEVEL_ROOT/"
cp -a Module.symvers "$DEVEL_ROOT/" 2>/dev/null || true
cp -a System.map "$DEVEL_ROOT/"
cp .config "$DEVEL_ROOT/"

# Copy Kconfig/Makefile tree (needed for module builds)
cp --parents $(find . -type f \( -name "Makefile" -o -name "Kconfig" \) \
    ! -path "./scripts/*" ! -path "./tools/*" ! -path "./Documentation/*") \
    "$DEVEL_ROOT/" 2>/dev/null || true

# Copy scripts/ (needed for module builds)
cp -a scripts "$DEVEL_ROOT/"
rm -rf "$DEVEL_ROOT/scripts/tracing"
rm -f "$DEVEL_ROOT/scripts/spdxcheck.py"

# Copy include/ (kernel headers)
cp -a include "$DEVEL_ROOT/"

# Copy arch/arm64 headers needed for module builds
mkdir -p "$DEVEL_ROOT/arch/arm64"
cp -a arch/arm64/include "$DEVEL_ROOT/arch/arm64/"
cp -a arch/arm64/Makefile "$DEVEL_ROOT/arch/arm64/" 2>/dev/null || true

# Copy tools/ build helpers
mkdir -p "$DEVEL_ROOT/tools/include/tools"
cp -a tools/include/tools/be_byteshift.h "$DEVEL_ROOT/tools/include/tools/" 2>/dev/null || true
cp -a tools/include/tools/le_byteshift.h "$DEVEL_ROOT/tools/include/tools/" 2>/dev/null || true
mkdir -p "$DEVEL_ROOT/tools/include/linux"
cp -a tools/include/linux/compiler.h "$DEVEL_ROOT/tools/include/linux/" 2>/dev/null || true
cp -a tools/include/linux/compiler_types.h "$DEVEL_ROOT/tools/include/linux/" 2>/dev/null || true
cp -a tools/include/linux/types.h "$DEVEL_ROOT/tools/include/linux/" 2>/dev/null || true
mkdir -p "$DEVEL_ROOT/tools/build"
cp -a tools/build/Build.include "$DEVEL_ROOT/tools/build/" 2>/dev/null || true
cp -a tools/build/Build "$DEVEL_ROOT/tools/build/" 2>/dev/null || true
cp -a tools/build/fixdep.c "$DEVEL_ROOT/tools/build/" 2>/dev/null || true

# SELinux headers (needed for make scripts)
mkdir -p "$DEVEL_ROOT/security/selinux/include"
cp -a security/selinux/include/classmap.h "$DEVEL_ROOT/security/selinux/include/" 2>/dev/null || true
cp -a security/selinux/include/initial_sid_to_string.h "$DEVEL_ROOT/security/selinux/include/" 2>/dev/null || true

# Generate UAPI headers and other build artifacts
make -C "$DEVEL_ROOT" ARCH=arm64 modules_prepare 2>/dev/null || \
    echo "Warning: modules_prepare had issues (may be OK for DKMS)"

# Clean up intermediate build artifacts
find "$DEVEL_ROOT" \( -name "*.o" -o -name "*.cmd" \) -delete 2>/dev/null || true
find "$DEVEL_ROOT/scripts" \( -name "*.o" -o -name "*.cmd" \) -delete 2>/dev/null || true

# ---- Create symlinks in /lib/modules for module build compatibility ----
mkdir -p %{buildroot}/lib/modules/%{kverstr}
ln -sf /usr/src/kernels/%{kverstr} %{buildroot}/lib/modules/%{kverstr}/build
ln -sf /usr/src/kernels/%{kverstr} %{buildroot}/lib/modules/%{kverstr}/source

# ============================================================================
# %%files - Package content
# ============================================================================

%files
%defattr(-,root,root)
/boot/vmlinuz-%{kverstr}
/boot/System.map-%{kverstr}
/boot/config-%{kverstr}
/boot/symvers-%{kverstr}
%dir /boot/dtb-%{kverstr}
/boot/dtb-%{kverstr}/*.dtb
/lib/modules/%{kverstr}
%exclude /lib/modules/%{kverstr}/build
%exclude /lib/modules/%{kverstr}/source

%files devel
%defattr(-,root,root)
/usr/src/kernels/%{kverstr}
/lib/modules/%{kverstr}/build
/lib/modules/%{kverstr}/source

# ============================================================================
# %%post / %%postun - Scriptlets
# ============================================================================

%post
# Update bootloader configuration
if [ -x /usr/bin/kernel-install ]; then
    /usr/bin/kernel-install add %{kverstr} /boot/vmlinuz-%{kverstr} || :
elif [ -x /usr/sbin/new-kernel-pkg ]; then
    /usr/sbin/new-kernel-pkg --package %{name} --rpmposttrans %{kverstr} || :
fi
/sbin/depmod -a %{kverstr} 2>/dev/null || :

%preun
if [ -x /usr/bin/kernel-install ]; then
    /usr/bin/kernel-install remove %{kverstr} || :
fi

%postun
if [ -x /usr/sbin/new-kernel-pkg ]; then
    /usr/sbin/new-kernel-pkg --package %{name} --rmpkg %{kverstr} || :
fi

# ============================================================================
# %%changelog
# ============================================================================

%changelog
* Sun May 11 2026 Cix Kernel Builder <builder@cix-copr> - 7.0.4-1
- Initial Copr build for Fedora 44 ARM64 (aarch64)
- Apply 32 Cix P1 SoC patches (0001-0028 + 2001-2004)
- Patches cover: ACPI, mailbox, SCMI, clk, reset, GPIO, I2C,
  USB Type-C, DP/HDMI, audio, DSP remoteproc, GPU panthor, PWM
- Use Cix defconfig for Orion O6 hardware
- Enable ZSTD module compression
