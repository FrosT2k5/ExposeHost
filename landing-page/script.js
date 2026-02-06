// Mobile nav toggle
const toggle = document.getElementById('navToggle');
const links = document.getElementById('navLinks');

if (toggle && links) {
    toggle.addEventListener('click', () => {
        toggle.classList.toggle('active');
        links.classList.toggle('open');
    });

    links.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            toggle.classList.remove('active');
            links.classList.remove('open');
        });
    });
}

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', e => {
        const href = anchor.getAttribute('href');
        if (href === '#') return;

        const target = document.querySelector(href);
        if (target) {
            e.preventDefault();
            const offset = 70;
            const pos = target.getBoundingClientRect().top + window.scrollY - offset;
            window.scrollTo({ top: pos, behavior: 'smooth' });
        }
    });
});

// GitHub Releases Fetcher
async function fetchReleases() {
    const releasesContainer = document.getElementById('releases-container');
    if (!releasesContainer) return;

    try {
        releasesContainer.innerHTML = '<div class="loading">Loading releases...</div>';
        const response = await fetch('https://api.github.com/repos/frost2k5/ExposeHost/releases');

        if (!response.ok) throw new Error('Failed to fetch releases');

        const releases = await response.json();

        if (releases.length === 0) {
            releasesContainer.innerHTML = '<p>No releases found.</p>';
            return;
        }

        releasesContainer.innerHTML = '';

        releases.forEach(release => {
            const date = new Date(release.published_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });

            const assetsHtml = release.assets.map(asset => `
                <a href="${asset.browser_download_url}" class="download-link" target="_blank">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                    </svg>
                    ${asset.name}
                    <span class="asset-size">(${formatBytes(asset.size)})</span>
                </a>
            `).join('');

            const releaseEl = document.createElement('div');
            releaseEl.className = 'release-card';
            releaseEl.innerHTML = `
                <div class="release-header">
                    <div class="release-title-row">
                        <h3>${release.name || release.tag_name}</h3>
                        ${release.prerelease ? '<span class="tag tag-pre">Pre-release</span>' : '<span class="tag tag-stable">Stable</span>'}
                    </div>
                    <span class="release-date">${date}</span>
                </div>
                
                <div class="release-body">
                    ${marked.parse(release.body)}
                </div>

                ${assetsHtml ? `
                <div class="release-assets">
                    <h4>Assets</h4>
                    <div class="assets-list">
                        ${assetsHtml}
                    </div>
                </div>
                ` : ''}
            `;

            releasesContainer.appendChild(releaseEl);
        });

    } catch (error) {
        console.error('Error fetching releases:', error);
        releasesContainer.innerHTML = `
            <div class="error-message">
                <p>Failed to load releases. Please check the <a href="https://github.com/frost2k5/ExposeHost/releases" target="_blank">GitHub repository</a> directly.</p>
            </div>
        `;
    }
}

function formatBytes(bytes, decimals = 2) {
    if (!+bytes) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

// Initialize releases if on releases page
if (document.getElementById('releases-container')) {
    fetchReleases();
}
