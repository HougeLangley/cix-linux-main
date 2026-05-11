# ============================================================================
# Copr build Makefile - "make srpm" method
#
# Copr invokes: make srpm spec=<specfile> outdir=<output-dir>
#   - $(spec):   Path to kernel-cix.spec (from the "Spec File" field)
#   - $(outdir): Directory to place the generated SRPM
#
# This Makefile:
#   1. Downloads Linux 7.0.4 kernel source tarball
#   2. Builds the SRPM from the spec file + patches + config
# ============================================================================

KERNEL_URL  := https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-7.0.4.tar.xz
KERNEL_TAR  := linux-7.0.4.tar.xz

.PHONY: srpm

srpm:
	@echo "=== Copr Cix Kernel SRPM Builder ==="

	# ---- Step 1: Download kernel source tarball ----
	@if [ -f "$(KERNEL_TAR)" ]; then \
		echo "[SKIP] $(KERNEL_TAR) already exists"; \
	else \
		echo "[DOWNLOAD] $(KERNEL_URL)"; \
		curl -fsSL -o "$(KERNEL_TAR)" "$(KERNEL_URL)" || { \
			echo "ERROR: Failed to download kernel source"; \
			echo "Trying wget as fallback..."; \
			wget -q -O "$(KERNEL_TAR)" "$(KERNEL_URL)" || exit 1; \
		}; \
	fi

	# ---- Step 2: Verify spec file and sources exist ----
	@if [ ! -f "$(spec)" ]; then \
		echo "ERROR: Spec file not found: $(spec)"; \
		echo "Contents of current directory:"; \
		ls -la; \
		exit 1; \
	fi
	@if [ ! -d "patches-7.0" ]; then \
		echo "ERROR: patches-7.0/ directory not found"; \
		exit 1; \
	fi
	@if [ ! -d "config" ]; then \
		echo "ERROR: config/ directory not found"; \
		exit 1; \
	fi
	@echo "[OK] Spec file and sources verified"

	# ---- Step 3: Count patches for build log ----
	@echo "Patches available: $$(ls patches-7.0/*.patch 2>/dev/null | wc -l)"

	# ---- Step 4: Build SRPM ----
	# _sourcedir = current directory (where tarball, patches, config live)
	# _srcrpmdir = output directory (where Copr expects the SRPM)
	@echo "=== Generating SRPM ==="
	rpmbuild -bs "$(spec)" \
		--define "_sourcedir $(CURDIR)" \
		--define "_srcrpmdir $(outdir)" \
		--define "_specdir $(CURDIR)" \
		--define "_builddir $(CURDIR)/build" \
		--define "_rpmdir $(CURDIR)/rpms" \
		|| { echo "ERROR: rpmbuild -bs failed"; exit 1; }

	@echo "=== SRPM generated in $(outdir) ==="
	@ls -lh "$(outdir)"/*.src.rpm 2>/dev/null || echo "WARNING: No SRPM found in $(outdir)"
