# ============================================================================
# Copr build Makefile - "make srpm" method
#
# Copr invokes: make srpm spec=<specfile> outdir=<output-dir>
#   - $(spec):   Path to kernel-cix.spec (from the "Spec File" field)
#   - $(outdir): Directory to place the generated SRPM
#
# This Makefile:
#   1. Downloads Linux 7.0.4 kernel source tarball
#   2. Creates a combined sources tarball (patches + config)
#   3. Builds the SRPM (rpmbuild includes only files listed as Source/Patch)
# ============================================================================

KERNEL_URL      := https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-7.0.4.tar.xz
KERNEL_TAR      := linux-7.0.4.tar.xz
CIX_SOURCES_TAR := cix-sources.tar.gz

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

	# ---- Step 2: Create combined sources tarball for rpmbuild ----
	# rpmbuild only packages files listed as Source/Patch in the spec.
	# We bundle patches + config into a tarball that Source1 references.
	@echo "[PACK] Creating $(CIX_SOURCES_TAR)"
	@tar czf "$(CIX_SOURCES_TAR)" patches-7.0/ config/ || { \
		echo "ERROR: Failed to create $(CIX_SOURCES_TAR)"; \
		exit 1; \
	}
	@echo "  Patches: $$(ls patches-7.0/*.patch 2>/dev/null | wc -l)"
	@echo "  Config:  $$(ls config/*.defconfig 2>/dev/null | wc -l) file(s)"

	# ---- Step 3: Verify spec file exists ----
	@if [ ! -f "$(spec)" ]; then \
		echo "ERROR: Spec file not found: $(spec)"; \
		exit 1; \
	fi
	@echo "[OK] All sources ready"

	# ---- Step 4: Build SRPM ----
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
