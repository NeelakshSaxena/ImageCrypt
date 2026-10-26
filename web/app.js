/* ===================================================================
   ImageCrypt - Computer Networks Lab Suite
   Frontend Client Application Logic
=================================================================== */

// Global State
const state = {
    role: 'sender',
    systemIp: '127.0.0.1',
    dataPort: 5000,
    webPort: 8080,
    config: null,
    stats: null,
    lastEventTimestamp: 0,
    selectedPacketId: null,
    autoScrollRaw: true,
    filterAction: 'all',
    intermediateNodeId: 1,
    bufferTotalChunks: 0,
    bufferReceivedMap: new Set(),
    isTransmitting: false
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initSenderControls();
    initIntermediateControls();
    initReceiverControls();
    initTopologyControls();
    initModal();

    // Initial Status Fetch
    fetchStatus();

    // Start Real-time Polling
    setInterval(fetchStatus, 1000);
    setInterval(fetchEvents, 600);
    setInterval(fetchRawPackets, 800);
});

/* ===================================================================
   NAVIGATION & TABS
=================================================================== */
function initTabs() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetScreenId = tab.getAttribute('data-tab');
            switchTab(targetScreenId);
        });
    });
}

function switchTab(screenId) {
    // Update active tab buttons
    document.querySelectorAll('.nav-tab').forEach(t => {
        t.classList.toggle('active', t.getAttribute('data-tab') === screenId);
    });

    // Update active screens
    document.querySelectorAll('.screen-view').forEach(s => {
        s.classList.toggle('active', s.id === screenId);
    });

    // Update active role notice
    const notice = document.getElementById('activeRoleNotice');
    if (notice) {
        const activeTab = document.querySelector(`.nav-tab[data-tab="${screenId}"]`);
        if (activeTab) {
            notice.textContent = `Perspective: ${activeTab.textContent.trim()}`;
        }
    }
}

/* ===================================================================
   SYSTEM STATUS & BANNER UPDATES
=================================================================== */
async function fetchStatus() {
    try {
        const res = await fetch('/api/status');
        if (!res.ok) return;
        const data = await res.json();
        
        state.role = data.role || state.role;
        state.systemIp = data.system_ip || state.systemIp;
        state.dataPort = data.transport_port || state.dataPort;
        state.webPort = data.web_port || state.webPort;
        state.config = data.config || state.config;
        state.stats = data.stats || state.stats;

        updateBanner();
        updateSenderScreenInfo();
        updateIntermediateScreenInfo();
        updateReceiverScreenInfo();
        updateTopologyView();
    } catch (e) {
        console.warn('Status poll warning:', e);
    }
}

function updateBanner() {
    const ipElem = document.getElementById('bannerSystemIp');
    const dataPortElem = document.getElementById('bannerDataPort');
    const webPortElem = document.getElementById('bannerWebPort');
    const badgeElem = document.getElementById('systemRoleBadge');

    if (ipElem) ipElem.textContent = state.systemIp;
    if (dataPortElem) dataPortElem.textContent = state.dataPort;
    if (webPortElem) webPortElem.textContent = state.webPort;

    if (badgeElem) {
        badgeElem.className = 'role-badge';
        if (state.role === 'sender') {
            badgeElem.classList.add('sender');
            badgeElem.textContent = 'SENDER SYSTEM';
        } else if (state.role.startsWith('intermediate')) {
            badgeElem.classList.add('intermediate');
            badgeElem.textContent = `INTERMEDIATE SYSTEM (${state.role.toUpperCase()})`;
        } else if (state.role === 'receiver') {
            badgeElem.classList.add('receiver');
            badgeElem.textContent = 'RECEIVER SYSTEM';
        } else {
            badgeElem.classList.add('sender');
            badgeElem.textContent = 'ALL-IN-ONE LAB DEMO';
        }
    }
}

/* ===================================================================
   SENDER SCREEN LOGIC
=================================================================== */
function initSenderControls() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const btnBrowse = document.getElementById('btnBrowse');
    const btnSample = document.getElementById('btnUseSample');
    const btnTransmit = document.getElementById('btnTransmitImage');
    const btnClearLog = document.getElementById('btnClearSenderLog');

    // File Browse
    if (btnBrowse && fileInput) {
        btnBrowse.addEventListener('click', () => fileInput.click());
    }

    // File Input change
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                uploadImageFile(e.target.files[0]);
            }
        });
    }

    // Drag and Drop
    if (dropZone) {
        ['dragenter', 'dragover'].forEach(name => {
            dropZone.addEventListener(name, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(name => {
            dropZone.addEventListener(name, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('dragover');
            });
        });

        dropZone.addEventListener('drop', (e) => {
            if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
                uploadImageFile(e.dataTransfer.files[0]);
            }
        });
    }

    // Sample Image Button
    if (btnSample) {
        btnSample.addEventListener('click', async () => {
            logSender('Loading standard lab sample image...');
            try {
                const res = await fetch('/api/use_sample', { method: 'POST' });
                const json = await res.json();
                if (json.success) {
                    logSender('Lab sample image loaded successfully.');
                    refreshPreviews();
                }
            } catch (err) {
                logSender(`Failed to load sample: ${err.message}`);
            }
        });
    }

    // Transmit Button
    if (btnTransmit) {
        btnTransmit.addEventListener('click', async () => {
            if (state.isTransmitting) return;
            state.isTransmitting = true;
            btnTransmit.disabled = true;
            btnTransmit.innerHTML = '<span class="btn-icon">⏳</span> Flooding Network in Progress...';

            logSender('--> Initiating Bit-Shuffle Encryption & Multi-Path Flooding...');
            const statusElem = document.getElementById('senderTxStatus');
            if (statusElem) {
                statusElem.textContent = 'Transmitting...';
                statusElem.className = 'text-cyan';
            }

            try {
                const res = await fetch('/api/transmit', { method: 'POST' });
                const json = await res.json();
                if (json.success) {
                    logSender(`[SUCCESS] Flooded ${json.total_chunks} fragments to all intermediate systems.`);
                    refreshPreviews();
                } else {
                    logSender(`[ERROR] Transmission failed: ${json.error}`);
                }
            } catch (err) {
                logSender(`[NETWORK ERROR] Could not trigger transmission: ${err.message}`);
            } finally {
                state.isTransmitting = false;
                btnTransmit.disabled = false;
                btnTransmit.innerHTML = '<span class="btn-icon">🚀</span> Start Network Flooding Transmission';
                if (statusElem) {
                    statusElem.textContent = 'Complete';
                    statusElem.className = 'text-emerald';
                }
            }
        });
    }

    if (btnClearLog) {
        btnClearLog.addEventListener('click', () => {
            const consoleBody = document.getElementById('senderDispatchLog');
            if (consoleBody) consoleBody.innerHTML = '<div class="log-line text-muted">[Log cleared]</div>';
        });
    }
}

async function uploadImageFile(file) {
    logSender(`Uploading image: ${file.name} (${Math.round(file.size / 1024)} KB)...`);
    const formData = new FormData();
    formData.append('image', file);

    try {
        const res = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        const json = await res.json();
        if (json.success) {
            logSender(`Image uploaded! Total fragments calculated: ${json.total_chunks}`);
            refreshPreviews();
        } else {
            logSender(`Upload failed: ${json.error}`);
        }
    } catch (err) {
        logSender(`Upload error: ${err.message}`);
    }
}

function refreshPreviews() {
    const t = new Date().getTime();
    const orig = document.getElementById('imgOriginalPreview');
    const enc = document.getElementById('imgEncryptedPreview');
    const rxEnc = document.getElementById('rxEncryptedNoiseImg');
    const rxOut = document.getElementById('rxReconstructedImg');

    if (orig) orig.src = `/api/image/original?t=${t}`;
    if (enc) enc.src = `/api/image/encrypted?t=${t}`;
    if (rxEnc) rxEnc.src = `/api/image/encrypted?t=${t}`;
    if (rxOut) rxOut.src = `/api/image/reconstructed?t=${t}`;
}

function logSender(msg) {
    const consoleBody = document.getElementById('senderDispatchLog');
    if (!consoleBody) return;
    const time = new Date().toLocaleTimeString();
    const line = document.createElement('div');
    line.className = 'log-line';
    line.textContent = `[${time}] ${msg}`;
    consoleBody.appendChild(line);
    consoleBody.scrollTop = consoleBody.scrollHeight;
}

function updateSenderScreenInfo() {
    const portElem = document.getElementById('senderAssignedPort');
    const ipElem = document.getElementById('senderAssignedIp');
    if (portElem && state.config && state.config.sender) {
        portElem.textContent = state.config.sender.port;
    }
    if (ipElem && state.config && state.config.sender) {
        ipElem.textContent = `IP: ${state.config.sender.ip}`;
    }

    // Populate target badges
    const badgesContainer = document.getElementById('senderTargetBadges');
    if (badgesContainer && state.config && state.config.intermediates) {
        badgesContainer.innerHTML = '';
        state.config.intermediates.forEach(intNode => {
            const pill = document.createElement('span');
            pill.className = 'target-pill';
            pill.textContent = `${intNode.name}: ${intNode.ip}:${intNode.port}`;
            badgesContainer.appendChild(pill);
        });
    }

    // Update metadata cards
    if (state.stats) {
        const metaDim = document.getElementById('metaDimensions');
        const metaSize = document.getElementById('metaSize');
        const metaChunks = document.getElementById('metaChunks');
        const metaNeighbors = document.getElementById('metaNeighbors');

        if (metaDim && state.stats.image_dimensions) metaDim.textContent = state.stats.image_dimensions;
        if (metaSize && state.stats.image_size_kb) metaSize.textContent = `${state.stats.image_size_kb} KB`;
        if (metaChunks && state.stats.total_chunks) metaChunks.textContent = `${state.stats.total_chunks} Chunks`;
        if (metaNeighbors && state.config && state.config.intermediates) {
            metaNeighbors.textContent = `${state.config.intermediates.length} Nodes`;
        }

        // Progress bar
        const sentPackets = state.stats.packets_sent || 0;
        const totalPackets = (state.stats.total_chunks || 1) * ((state.config && state.config.intermediates) ? state.config.intermediates.length : 3);
        const percent = Math.min(100, Math.round((sentPackets / (totalPackets || 1)) * 100));

        const bar = document.getElementById('senderProgressBar');
        const pLabel = document.getElementById('senderProgressPercent');
        const pSent = document.getElementById('senderPacketsSent');
        const bSent = document.getElementById('senderBytesSent');

        if (bar) bar.style.width = `${percent}%`;
        if (pLabel) pLabel.textContent = `${percent}%`;
        if (pSent) pSent.textContent = sentPackets;
        if (bSent && state.stats.bytes_sent) bSent.textContent = state.stats.bytes_sent;
    }
}

/* ===================================================================
   INTERMEDIATE SCREEN LOGIC (RAW DATA STREAM)
=================================================================== */
function initIntermediateControls() {
    const selector = document.getElementById('selectIntermediateNode');
    const filterSelect = document.getElementById('rawFilterAction');
    const btnAutoScroll = document.getElementById('btnToggleAutoScroll');
    const btnClearStream = document.getElementById('btnClearRawStream');

    if (selector) {
        selector.addEventListener('change', (e) => {
            state.intermediateNodeId = parseInt(e.target.value, 10);
            updateIntermediateScreenInfo();
            fetchRawPackets();
        });
    }

    if (filterSelect) {
        filterSelect.addEventListener('change', (e) => {
            state.filterAction = e.target.value;
            renderRawStream();
        });
    }

    if (btnAutoScroll) {
        btnAutoScroll.addEventListener('click', () => {
            state.autoScrollRaw = !state.autoScrollRaw;
            btnAutoScroll.textContent = `Auto-scroll: ${state.autoScrollRaw ? 'ON' : 'OFF'}`;
        });
    }

    if (btnClearStream) {
        btnClearStream.addEventListener('click', async () => {
            await fetch(`/api/clear_raw?node_id=${state.intermediateNodeId}`, { method: 'POST' });
            rawPacketsCache = [];
            renderRawStream();
        });
    }
}

function updateIntermediateScreenInfo() {
    if (!state.config || !state.config.intermediates) return;

    // Populate selector dropdown if empty
    const selector = document.getElementById('selectIntermediateNode');
    if (selector && selector.children.length === 0) {
        state.config.intermediates.forEach(node => {
            const opt = document.createElement('option');
            opt.value = node.id;
            opt.textContent = `${node.name} (${node.ip}:${node.port})`;
            selector.appendChild(opt);
        });
    }

    const currentNode = state.config.intermediates.find(n => n.id === state.intermediateNodeId) || state.config.intermediates[0];
    if (currentNode) {
        const badge = document.getElementById('intermediateBadge');
        const roleName = document.getElementById('intNodeRoleName');
        const ipElem = document.getElementById('intNodeIp');
        const portElem = document.getElementById('intNodePort');
        const listenPort = document.getElementById('rawListenPort');
        const forwardTarget = document.getElementById('intForwardTarget');

        if (badge) badge.textContent = currentNode.name;
        if (roleName) roleName.textContent = currentNode.name;
        if (ipElem) ipElem.textContent = currentNode.ip;
        if (portElem) portElem.textContent = currentNode.port;
        if (listenPort) listenPort.textContent = currentNode.port;

        if (forwardTarget && state.config.receiver) {
            forwardTarget.textContent = `Receiver (${state.config.receiver.ip}:${state.config.receiver.port})`;
        }
    }

    // Update Intermediate KPIs
    if (state.stats && state.stats.intermediates && state.stats.intermediates[state.intermediateNodeId]) {
        const iStats = state.stats.intermediates[state.intermediateNodeId];
        const rec = document.getElementById('intTotalReceived');
        const fwd = document.getElementById('intTotalForwarded');
        const dup = document.getElementById('intDuplicatesDropped');
        const ttl = document.getElementById('intTtlDropped');

        if (rec) rec.textContent = iStats.received || 0;
        if (fwd) fwd.textContent = iStats.forwarded || 0;
        if (dup) dup.textContent = iStats.duplicates_dropped || 0;
        if (ttl) ttl.textContent = iStats.ttl_dropped || 0;
    }
}

let rawPacketsCache = [];

async function fetchRawPackets() {
    try {
        const res = await fetch(`/api/raw_packets?node_id=${state.intermediateNodeId}`);
        if (!res.ok) return;
        const data = await res.json();
        if (data && data.packets) {
            rawPacketsCache = data.packets;
            renderRawStream();
        }
    } catch (e) {
        console.warn('Error fetching raw packets:', e);
    }
}

function renderRawStream() {
    const streamContainer = document.getElementById('rawPacketStream');
    if (!streamContainer) return;

    // Filter packets
    let filtered = rawPacketsCache;
    if (state.filterAction === 'forwarded') {
        filtered = filtered.filter(p => p.action === 'FORWARDED');
    } else if (state.filterAction === 'duplicate') {
        filtered = filtered.filter(p => p.action === 'DROPPED_DUPLICATE');
    } else if (state.filterAction === 'ttl') {
        filtered = filtered.filter(p => p.action === 'DROPPED_TTL');
    }

    if (filtered.length === 0) {
        streamContainer.innerHTML = `
            <div class="stream-empty-notice">
                <div class="empty-icon">📡</div>
                <p>No packets matching filter for this intermediary.</p>
                <span class="empty-hint">Packets will stream here when Node A transmits.</span>
            </div>
        `;
        return;
    }

    streamContainer.innerHTML = '';
    filtered.forEach(pkt => {
        const item = document.createElement('div');
        item.className = 'packet-item-card';
        if (pkt.packet_id === state.selectedPacketId) item.classList.add('selected');

        let pillClass = 'forwarded';
        let actionLabel = 'FORWARDED';
        if (pkt.action === 'DROPPED_DUPLICATE') {
            pillClass = 'duplicate';
            actionLabel = 'DUPLICATE DROP';
        } else if (pkt.action === 'DROPPED_TTL') {
            pillClass = 'ttl';
            actionLabel = 'TTL EXPIRED';
        }

        item.innerHTML = `
            <div class="packet-item-top">
                <span class="packet-title mono">PKT #${pkt.packet_id}</span>
                <span class="action-pill ${pillClass}">${actionLabel}</span>
            </div>
            <div class="packet-item-details">
                <span>Seq: <strong>${pkt.chunk_sequence}/${pkt.total_chunks}</strong></span>
                <span>TTL: <strong>${pkt.ttl}</strong></span>
                <span>Size: <strong>${pkt.payload_length}B</strong></span>
                <span>Time: <strong>${pkt.time || ''}</strong></span>
            </div>
        `;

        item.addEventListener('click', () => {
            selectPacketForInspection(pkt);
        });

        streamContainer.appendChild(item);
    });

    if (state.autoScrollRaw) {
        streamContainer.scrollTop = streamContainer.scrollHeight;
    }

    // Auto-select first packet if none selected
    if (!state.selectedPacketId && filtered.length > 0) {
        selectPacketForInspection(filtered[filtered.length - 1]);
    }
}

function selectPacketForInspection(pkt) {
    state.selectedPacketId = pkt.packet_id;

    // Highlight card
    document.querySelectorAll('.packet-item-card').forEach(c => c.classList.remove('selected'));

    const tag = document.getElementById('inspPacketTag');
    const hMagic = document.getElementById('hdrMagic');
    const hSrc = document.getElementById('hdrSrcId');
    const hDest = document.getElementById('hdrDestId');
    const hPktId = document.getElementById('hdrPacketId');
    const hChunkSeq = document.getElementById('hdrChunkSeq');
    const hTotalChunks = document.getElementById('hdrTotalChunks');
    const hTtl = document.getElementById('hdrTtl');
    const hPayloadLen = document.getElementById('hdrPayloadLen');
    const decText = document.getElementById('inspDecisionText');
    const hexContent = document.getElementById('inspHexDump');

    if (tag) tag.textContent = `#${pkt.packet_id}`;
    if (hMagic) hMagic.textContent = pkt.magic || 'IMGF';
    if (hSrc) hSrc.textContent = `${pkt.src_id} (Sender A)`;
    if (hDest) hDest.textContent = `${pkt.dest_id} (Receiver E)`;
    if (hPktId) hPktId.textContent = pkt.packet_id;
    if (hChunkSeq) hChunkSeq.textContent = `Chunk ${pkt.chunk_sequence}`;
    if (hTotalChunks) hTotalChunks.textContent = `${pkt.total_chunks} total`;
    if (hTtl) hTtl.textContent = `${pkt.ttl} hops remaining`;
    if (hPayloadLen) hPayloadLen.textContent = `${pkt.payload_length} bytes`;

    if (decText) {
        if (pkt.action === 'FORWARDED') {
            decText.innerHTML = `<span class="text-emerald"><strong>[FORWARDED]</strong> Packet is new and TTL &gt; 0. Forwarding to Receiver (${state.config.receiver.ip}:${state.config.receiver.port})</span>`;
        } else if (pkt.action === 'DROPPED_DUPLICATE') {
            decText.innerHTML = `<span class="text-red"><strong>[DROPPED]</strong> Duplicate packet ID #${pkt.packet_id} already processed. Dropped to break network loop.</span>`;
        } else if (pkt.action === 'DROPPED_TTL') {
            decText.innerHTML = `<span class="text-amber"><strong>[DROPPED]</strong> TTL reached 0. Packet expired to prevent infinite circulation.</span>`;
        }
    }

    if (hexContent) {
        hexContent.textContent = pkt.hexdump || 'No hex dump available';
    }
}

/* ===================================================================
   RECEIVER SCREEN LOGIC
=================================================================== */
function initReceiverControls() {
    // Receiver-specific controls
}

function updateReceiverScreenInfo() {
    if (!state.config || !state.config.receiver) return;

    const rPort = document.getElementById('receiverAssignedPort');
    const rIp = document.getElementById('receiverAssignedIp');
    if (rPort) rPort.textContent = state.config.receiver.port;
    if (rIp) rIp.textContent = `IP: ${state.config.receiver.ip}`;

    if (!state.stats) return;

    const rChunks = document.getElementById('rxChunksReceived');
    const rDups = document.getElementById('rxDuplicatesFiltered');
    const rDecStatus = document.getElementById('rxDecryptionStatus');
    const rHash = document.getElementById('rxSha256Match');
    const rBadge = document.getElementById('rxSuccessBadge');
    const dlBtn = document.getElementById('btnDownloadImage');
    const hashBox = document.getElementById('rxHashDisplay');

    const totalChunks = state.stats.total_chunks || 0;
    const receivedChunks = state.stats.chunks_received || 0;

    if (rChunks) rChunks.textContent = `${receivedChunks} / ${totalChunks}`;
    if (rDups) rDups.textContent = state.stats.duplicates_dropped || 0;

    if (state.stats.reassembled) {
        if (rDecStatus) {
            rDecStatus.textContent = 'Decrypted & Verified';
            rDecStatus.className = 'stat-num text-emerald';
        }
        if (rBadge) {
            rBadge.textContent = '100% Verified Match';
            rBadge.className = 'badge badge-emerald';
        }
        if (rHash) {
            rHash.textContent = 'PASS (Match)';
            rHash.className = 'stat-num text-emerald';
        }
        if (dlBtn) dlBtn.classList.remove('disabled');
        if (hashBox && state.stats.sha256) {
            hashBox.textContent = `SHA-256: ${state.stats.sha256} [Verified Byte-Exact]`;
        }
    } else {
        if (receivedChunks > 0) {
            if (rDecStatus) rDecStatus.textContent = `Collecting (${Math.round((receivedChunks/totalChunks)*100)}%)`;
        } else {
            if (rDecStatus) rDecStatus.textContent = 'Waiting';
        }
    }

    // Render buffer matrix
    renderBufferMatrix(totalChunks, state.stats.received_chunk_indices || []);
}

function renderBufferMatrix(total, receivedList) {
    const grid = document.getElementById('rxBufferGrid');
    if (!grid) return;

    if (total === 0) {
        grid.innerHTML = '<div class="buffer-empty-msg">No transmission active. Waiting for Sender to flood image fragments...</div>';
        return;
    }

    const receivedSet = new Set(receivedList);
    // If chunk count changed, rebuild grid
    if (state.bufferTotalChunks !== total) {
        state.bufferTotalChunks = total;
        grid.innerHTML = '';
        for (let i = 0; i < total; i++) {
            const cell = document.createElement('div');
            cell.className = 'buffer-cell';
            cell.id = `buf-cell-${i}`;
            cell.innerHTML = `<span>#${i}</span>`;
            grid.appendChild(cell);
        }
    }

    // Update cells status
    for (let i = 0; i < total; i++) {
        const cell = document.getElementById(`buf-cell-${i}`);
        if (cell) {
            if (state.stats.reassembled) {
                cell.className = 'buffer-cell reassembled';
            } else if (receivedSet.has(i)) {
                cell.className = 'buffer-cell received';
            } else {
                cell.className = 'buffer-cell';
            }
        }
    }
}

/* ===================================================================
   TOPOLOGY SCREEN & DIAGNOSTICS
=================================================================== */
function initTopologyControls() {
    const btnRefresh = document.getElementById('btnRefreshDiagnostics');
    const btnRunTest = document.getElementById('btnRunTest');

    if (btnRefresh) {
        btnRefresh.addEventListener('click', runConnectionTest);
    }
    if (btnRunTest) {
        btnRunTest.addEventListener('click', runConnectionTest);
    }
}

function updateTopologyView() {
    if (!state.config) return;

    const sIp = document.getElementById('topoSenderIp');
    const rIp = document.getElementById('topoReceiverIp');

    if (sIp && state.config.sender) {
        sIp.textContent = `${state.config.sender.ip}:${state.config.sender.port}`;
    }
    if (rIp && state.config.receiver) {
        rIp.textContent = `${state.config.receiver.ip}:${state.config.receiver.port}`;
    }

    // Intermediate nodes column in diagram
    const intCol = document.getElementById('topoIntermediatesCol');
    if (intCol && state.config.intermediates) {
        intCol.innerHTML = '';
        state.config.intermediates.forEach(node => {
            const card = document.createElement('div');
            card.className = 'topo-node-card intermediate-card';
            card.innerHTML = `
                <div class="node-icon">🔀</div>
                <div class="node-title">${node.name}</div>
                <div class="node-ip mono">${node.ip}:${node.port}</div>
                <span class="node-status-pill online">Routing</span>
            `;
            intCol.appendChild(card);
        });
    }

    // Table view
    const tbody = document.getElementById('nodesTableBody');
    if (tbody) {
        tbody.innerHTML = '';

        // Sender
        if (state.config.sender) {
            tbody.innerHTML += `
                <tr>
                    <td><span class="badge">0</span></td>
                    <td><strong>Node A (Sender)</strong></td>
                    <td class="mono">${state.config.sender.ip}</td>
                    <td class="mono text-cyan">${state.config.sender.port}</td>
                    <td class="mono text-purple">${state.webPort}</td>
                    <td><span class="node-status-pill online">ONLINE</span></td>
                </tr>
            `;
        }

        // Intermediates
        if (state.config.intermediates) {
            state.config.intermediates.forEach(n => {
                tbody.innerHTML += `
                    <tr>
                        <td><span class="badge badge-amber">${n.id}</span></td>
                        <td><strong>${n.name}</strong></td>
                        <td class="mono">${n.ip}</td>
                        <td class="mono text-cyan">${n.port}</td>
                        <td class="mono text-purple">--</td>
                        <td><span class="node-status-pill online">CONNECTED</span></td>
                    </tr>
                `;
            });
        }

        // Receiver
        if (state.config.receiver) {
            tbody.innerHTML += `
                <tr>
                    <td><span class="badge badge-emerald">4</span></td>
                    <td><strong>Node E (Receiver)</strong></td>
                    <td class="mono">${state.config.receiver.ip}</td>
                    <td class="mono text-cyan">${state.config.receiver.port}</td>
                    <td class="mono text-purple">--</td>
                    <td><span class="node-status-pill online">LISTENING</span></td>
                </tr>
            `;
        }
    }
}

/* ===================================================================
   CONNECTION TEST MODAL
=================================================================== */
function initModal() {
    const modal = document.getElementById('testModal');
    const closeBtn = document.getElementById('btnCloseModal');
    const footerClose = document.getElementById('btnModalClose');

    [closeBtn, footerClose].forEach(btn => {
        if (btn) btn.addEventListener('click', () => {
            if (modal) modal.style.display = 'none';
        });
    });
}

async function runConnectionTest() {
    const modal = document.getElementById('testModal');
    const list = document.getElementById('modalTestList');
    if (modal) modal.style.display = 'flex';
    if (list) list.innerHTML = '<div class="test-row"><span>Probing network links...</span><span>⏳</span></div>';

    try {
        const res = await fetch('/api/test_connections', { method: 'POST' });
        const data = await res.json();

        if (list && data.results) {
            list.innerHTML = '';
            data.results.forEach(r => {
                const row = document.createElement('div');
                row.className = 'test-row';
                const passClass = r.status === 'OK' ? 'pass' : 'fail';
                row.innerHTML = `
                    <span><strong>${r.node}</strong> (${r.target})</span>
                    <span class="test-status ${passClass}">${r.status === 'OK' ? '✓ READY' : '✗ ' + r.error}</span>
                `;
                list.appendChild(row);
            });
        }
    } catch (err) {
        if (list) {
            list.innerHTML = `<div class="test-row"><span class="text-red">Error running test: ${err.message}</span></div>`;
        }
    }
}

/* ===================================================================
   EVENT LOG STREAM
=================================================================== */
async function fetchEvents() {
    try {
        const res = await fetch(`/api/events?since=${state.lastEventTimestamp}`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.events && data.events.length > 0) {
            data.events.forEach(ev => {
                state.lastEventTimestamp = Math.max(state.lastEventTimestamp, ev.timestamp || 0);
                if (ev.type === 'send') {
                    logSender(ev.message);
                }
                if (ev.type === 'reassembled') {
                    refreshPreviews();
                }
            });
        }
    } catch (e) {
        // Polling error silently handled
    }
}
