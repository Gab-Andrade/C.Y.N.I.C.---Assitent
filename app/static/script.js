(() => {
'use strict';

/* =====================================================================
   C.Y.N.I.C. — HUD 3D
   Protocolo com o backend (inalterado): WebSocket /ws  ->  { estado, mensagem }
   Estados: pronto | ouvindo | processando | respondendo
   ===================================================================== */

const $ = (id) => document.getElementById(id);
const lerp = (a, b, t) => a + (b - a) * t;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const pad = (n) => String(n).padStart(2, '0');
const TAU = Math.PI * 2;
const reduzMov = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* cor = tom do 3D | giro = rotação do cérebro | aneis = velocidade dos anéis
   brilho = intensidade geral | pulso = quanto o núcleo reage à "voz" */
const ESTADOS = {
    offline:     { rotulo: 'SEM CONEXÃO',  cor: 0x2f6b45, giro: 0.05, aneis: 0.4, brilho: 0.30, pulso: 0.0 },
    pronto:      { rotulo: 'ONLINE',       cor: 0x00ff66, giro: 0.18, aneis: 1.0, brilho: 0.85, pulso: 0.15 },
    ouvindo:     { rotulo: 'ESCUTANDO',    cor: 0x00ff66, giro: 0.30, aneis: 1.6, brilho: 1.00, pulso: 0.30 },
    processando: { rotulo: 'PROCESSANDO',  cor: 0xb6ffcf, giro: 1.10, aneis: 5.0, brilho: 1.35, pulso: 0.60 },
    respondendo: { rotulo: 'RESPONDENDO',  cor: 0x39ff14, giro: 0.45, aneis: 2.4, brilho: 1.45, pulso: 1.00 }
};

/* níveis de qualidade (0 = mais leve) */
const QUALIDADES = [
    { nome: 'BAIXA', pr: 0.75, poeira: 400 },
    { nome: 'MÉDIA', pr: 1.0,  poeira: 1000  },
    { nome: 'ALTA',  pr: Math.min(window.devicePixelRatio || 1, 1.5), poeira: 2200 }
];
let qualidade = 2;
try {
    const q = parseInt(localStorage.getItem('cynic-q'), 10);
    if (q >= 0 && q <= 2) qualidade = q;
} catch (_) { /* sem storage, segue o jogo */ }

const el = {
    estado: $('estado'), msg: $('status'), log: $('log'),
    relogio: $('relogio'), data: $('data'), conexao: $('conexao'),
    fps: $('m-fps'), mem: $('m-mem'), lat: $('m-lat'), med: $('m-med'),
    turnos: $('m-turnos'), up: $('m-up'),
    bNucleo: $('b-nucleo'), bSinapses: $('b-sinapses'), bFluxo: $('b-fluxo'),
    btnQ: $('b-q'), btnM: $('b-m'), btnF: $('b-f'),
    boot: $('boot'), bootLinhas: $('boot-linhas')
};

const mouse = { x: 0, y: 0 };
window.addEventListener('pointermove', (e) => {
    mouse.x = (e.clientX / window.innerWidth - 0.5) * 2;
    mouse.y = -(e.clientY / window.innerHeight - 0.5) * 2;
});

/* =====================================================================
   CENA 3D (Three.js)
   ===================================================================== */
function criarCena() {
    const canvas = $('cena');
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setClearColor(0x000000, 0);

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x000000, 16, 60);
    const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 200);

    const corAtual = new THREE.Color(0x00ff66);
    const corAlvo = new THREE.Color(0x00ff66);
    const tintaveis = [];
    let brilho = 0.3, giro = 0.05, aneis = 0.4;
    const girantes = []; // [objeto, vx, vy, vz]

    /* textura de brilho (bolinha difusa) */
    const brilhoTex = (() => {
        const c = document.createElement('canvas');
        c.width = c.height = 64;
        const g = c.getContext('2d');
        const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
        gr.addColorStop(0, 'rgba(255,255,255,1)');
        gr.addColorStop(0.25, 'rgba(255,255,255,0.55)');
        gr.addColorStop(1, 'rgba(255,255,255,0)');
        g.fillStyle = gr;
        g.fillRect(0, 0, 64, 64);
        return new THREE.CanvasTexture(c);
    })();

    /* fábrica de materiais (todos aditivos e "tingíveis" pelo estado) */
    const reg = (m, op) => {
        m.userData.op = op;
        m.transparent = true;
        m.opacity = op;
        m.depthWrite = false;
        tintaveis.push(m);
        return m;
    };
    const ADD = THREE.AdditiveBlending;
    const matLinha  = (op) => reg(new THREE.LineBasicMaterial({ color: 0x00ff66, blending: ADD, fog: false }), op);
    const matMalha  = (op) => reg(new THREE.MeshBasicMaterial({ color: 0x00ff66, wireframe: true, blending: ADD, fog: false }), op);
    const matSolido = (op) => reg(new THREE.MeshBasicMaterial({ color: 0x00ff66, blending: ADD, fog: false }), op);
    const matPonto  = (tam, op, fog) => reg(new THREE.PointsMaterial({ color: 0x00ff66, size: tam, map: brilhoTex, blending: ADD, sizeAttenuation: true, fog: !!fog }), op);

    /* ---------- grupo central ---------- */
    const nucleo = new THREE.Group();
    nucleo.position.y = 1.1;
    scene.add(nucleo);

    /* cérebro neural: nós + sinapses + pulsos viajando */
    const cerebro = new THREE.Group();
    nucleo.add(cerebro);

    const N = 230;
    const nosPos = [];
    const dourado = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < N; i++) {
        const y = 1 - (i / (N - 1)) * 2;
        const r = Math.sqrt(1 - y * y);
        const a = dourado * i;
        const x = Math.cos(a) * r, z = Math.sin(a) * r;
        const g = 1 + 0.09 * Math.sin(x * 6 + y * 4) * Math.cos(z * 5) + 0.05 * Math.sin(y * 11 + z * 6);
        nosPos.push(new THREE.Vector3(x * 1.4 * g + (x >= 0 ? 0.07 : -0.07), y * 1.0 * g, z * 1.15 * g));
    }

    const arestas = [];
    const vistos = new Set();
    const addAresta = (i, j) => {
        const k = i < j ? i + '-' + j : j + '-' + i;
        if (i !== j && !vistos.has(k)) { vistos.add(k); arestas.push([i, j]); }
    };
    for (let i = 0; i < N; i++) {
        nosPos
            .map((p, j) => [j, p.distanceToSquared(nosPos[i])])
            .filter(([j]) => j !== i)
            .sort((a, b) => a[1] - b[1])
            .slice(0, 3)
            .forEach(([j]) => addAresta(i, j));
    }
    for (let n = 0; n < 14; n++) { // ligações entre hemisférios
        const i = (Math.random() * N) | 0;
        let j = (Math.random() * N) | 0;
        if (Math.sign(nosPos[i].x) !== Math.sign(nosPos[j].x)) addAresta(i, j);
    }

    const linhasArr = new Float32Array(arestas.length * 6);
    arestas.forEach(([a, b], i) => {
        nosPos[a].toArray(linhasArr, i * 6);
        nosPos[b].toArray(linhasArr, i * 6 + 3);
    });
    const linhasGeo = new THREE.BufferGeometry();
    linhasGeo.setAttribute('position', new THREE.BufferAttribute(linhasArr, 3));
    cerebro.add(new THREE.LineSegments(linhasGeo, matLinha(0.45)));

    const nosArr = new Float32Array(N * 3);
    nosPos.forEach((p, i) => p.toArray(nosArr, i * 3));
    const nosGeo = new THREE.BufferGeometry();
    nosGeo.setAttribute('position', new THREE.BufferAttribute(nosArr, 3));
    cerebro.add(new THREE.Points(nosGeo, matPonto(0.11, 0.9)));

    const adj = Array.from({ length: N }, () => []);
    arestas.forEach(([a, b], i) => { adj[a].push(i); adj[b].push(i); });

    const NP = 42;
    const pulsos = Array.from({ length: NP }, () => ({ from: 0, to: 0, t: Math.random(), v: 0.5 + Math.random() * 0.9 }));
    const novoPulso = (p, from) => {
        p.from = from;
        const es = adj[from];
        const [a, b] = arestas[es[(Math.random() * es.length) | 0]];
        p.to = a === from ? b : a;
        p.t = 0;
    };
    pulsos.forEach((p) => novoPulso(p, (Math.random() * N) | 0));
    const pulsoArr = new Float32Array(NP * 3);
    const pulsoGeo = new THREE.BufferGeometry();
    pulsoGeo.setAttribute('position', new THREE.BufferAttribute(pulsoArr, 3));
    cerebro.add(new THREE.Points(pulsoGeo, matPonto(0.28, 1)));

    /* halo central */
    const halo = new THREE.Sprite(reg(new THREE.SpriteMaterial({ map: brilhoTex, color: 0x00ff66, blending: ADD, fog: false }), 0.5));
    halo.scale.setScalar(6.5);
    nucleo.add(halo);

    /* cascas de contenção */
    const casca1 = new THREE.Mesh(new THREE.IcosahedronGeometry(1.95, 1), matMalha(0.16));
    const casca2 = new THREE.Mesh(new THREE.IcosahedronGeometry(4.6, 2), matMalha(0.05));
    nucleo.add(casca1, casca2);

    /* arcos grossos estilo HUD */
    for (let k = 0; k < 3; k++) {
        const arco = new THREE.Mesh(new THREE.TorusGeometry(2.25, 0.035, 6, 64, 1.0 + k * 0.55), matSolido(0.9));
        arco.rotation.z = k * 2.1;
        nucleo.add(arco);
        girantes.push([arco, 0, 0, (k % 2 ? -1 : 1) * (0.5 + k * 0.3)]);
    }

    /* anéis giroscópio */
    const giroscopio = (raio, tubo, tx, ty, vel, op) => {
        const piv = new THREE.Group();
        piv.rotation.set(tx, ty, 0);
        const anel = new THREE.Mesh(new THREE.TorusGeometry(raio, tubo, 6, 160), matSolido(op));
        piv.add(anel);
        nucleo.add(piv);
        girantes.push([anel, 0, 0, vel]);
        girantes.push([piv, 0.06, 0, 0]);
    };
    giroscopio(3.25, 0.012, 1.15, 0.2, 0.35, 0.8);
    giroscopio(3.5, 0.008, -0.9, 0.6, -0.25, 0.6);

    /* anel tracejado */
    const dashPts = [];
    for (let i = 0; i <= 128; i++) {
        const a = (i / 128) * TAU;
        dashPts.push(new THREE.Vector3(Math.cos(a) * 3.8, Math.sin(a) * 3.8, 0));
    }
    const dash = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(dashPts),
        reg(new THREE.LineDashedMaterial({ color: 0x00ff66, dashSize: 0.18, gapSize: 0.12, blending: ADD, fog: false }), 0.7)
    );
    dash.computeLineDistances();
    const dashPiv = new THREE.Group();
    dashPiv.rotation.x = 0.35;
    dashPiv.add(dash);
    nucleo.add(dashPiv);
    girantes.push([dash, 0, 0, 0.12]);

    /* dial com marcações */
    const tk = [];
    for (let i = 0; i < 180; i++) {
        const a = (i / 180) * TAU;
        const len = i % 15 === 0 ? 0.36 : i % 5 === 0 ? 0.2 : 0.09;
        const c = Math.cos(a), s = Math.sin(a), r0 = 4.05;
        tk.push(c * r0, s * r0, 0, c * (r0 + len), s * (r0 + len), 0);
    }
    const dialGeo = new THREE.BufferGeometry();
    dialGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(tk), 3));
    const dial = new THREE.LineSegments(dialGeo, matLinha(0.55));
    nucleo.add(dial);
    girantes.push([dial, 0, 0, -0.08]);

    /* espectro circular (reage à "voz") */
    const NB = 72;
    const espArr = new Float32Array(NB * 6);
    const espGeo = new THREE.BufferGeometry();
    espGeo.setAttribute('position', new THREE.BufferAttribute(espArr, 3));
    nucleo.add(new THREE.LineSegments(espGeo, matLinha(1)));

    /* satélites em órbita */
    const satelite = (raio, inc, vel, tam) => {
        const tilt = new THREE.Group();
        tilt.rotation.x = inc;
        const orb = [];
        for (let i = 0; i <= 96; i++) { const a = (i / 96) * TAU; orb.push(new THREE.Vector3(Math.cos(a) * raio, 0, Math.sin(a) * raio)); }
        tilt.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(orb), matLinha(0.12)));
        const piv = new THREE.Group();
        const m = new THREE.Mesh(new THREE.OctahedronGeometry(tam, 0), matMalha(1));
        m.position.x = raio;
        piv.add(m);
        tilt.add(piv);
        nucleo.add(tilt);
        girantes.push([piv, 0, vel, 0]);
        girantes.push([m, 1.5, 2.2, 0]);
    };
    satelite(2.9, 0.5, 0.7, 0.14);
    satelite(3.6, -0.8, -0.5, 0.18);
    satelite(4.4, 1.2, 0.35, 0.12);
    satelite(3.2, -0.2, -0.9, 0.1);

    /* hologramas laterais */
    const laterais = new THREE.Group();
    laterais.position.set(0, 1.1, -2);
    scene.add(laterais);
    const holoE = new THREE.Group();
    const holoD = new THREE.Group();
    const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(0.75, 0.2, 100, 10), matMalha(0.4));
    holoE.add(knot);
    const globo = new THREE.Mesh(new THREE.SphereGeometry(1, 18, 12), matMalha(0.35));
    const anelGlobo = new THREE.Mesh(new THREE.TorusGeometry(1.5, 0.01, 6, 80), matSolido(0.8));
    anelGlobo.rotation.x = 1.2;
    holoD.add(globo, anelGlobo);
    laterais.add(holoE, holoD);
    girantes.push([knot, 0.3, 0.5, 0.1], [globo, 0, 0.4, 0], [anelGlobo, 0, 0, 0.5]);

    /* poeira estelar */
    const POEIRA_MAX = 2200;
    const poeiraArr = new Float32Array(POEIRA_MAX * 3);
    for (let i = 0; i < POEIRA_MAX; i++) {
        poeiraArr[i * 3]     = (Math.random() - 0.5) * 60;
        poeiraArr[i * 3 + 1] = (Math.random() - 0.5) * 34;
        poeiraArr[i * 3 + 2] = -30 + Math.random() * 34;
    }
    const poeiraGeo = new THREE.BufferGeometry();
    poeiraGeo.setAttribute('position', new THREE.BufferAttribute(poeiraArr, 3));
    const poeira = new THREE.Points(poeiraGeo, matPonto(0.1, 0.6, true));
    scene.add(poeira);

    /* túnel de grades (chão e teto) */
    const chao = new THREE.GridHelper(120, 60, 0x00ff66, 0x00ff66);
    chao.position.y = -6.5;
    const teto = new THREE.GridHelper(120, 60, 0x00ff66, 0x00ff66);
    teto.position.y = 10;
    [chao, teto].forEach((g) => {
        g.material.transparent = true;
        g.material.opacity = 0.2;
        g.material.blending = ADD;
        g.material.depthWrite = false;
    });
    teto.material = chao.material.clone();
    teto.material.opacity = 0.08;
    scene.add(chao, teto);

    /* ---------- API ---------- */
    function aplicarQualidade(q) {
        const cfg = QUALIDADES[q];
        renderer.setPixelRatio(cfg.pr);
        poeiraGeo.setDrawRange(0, cfg.poeira);
        redimensionar();
    }

    function redimensionar() {
        const w = window.innerWidth, h = window.innerHeight;
        renderer.setSize(w, h, false);
        const asp = w / h;
        camera.aspect = asp;
        camera.position.z = asp < 1.1 ? 17 : 12.5;
        camera.updateProjectionMatrix();
        const meia = Math.tan((camera.fov * Math.PI) / 360) * (camera.position.z + 2) * asp;
        holoE.position.x = -meia * 0.58;
        holoD.position.x = meia * 0.58;
        laterais.visible = asp > 1.5;
    }

    const tmpV = new THREE.Vector3();
    function atualizar(dt, t, cfg, amp) {
        const k = 1 - Math.exp(-dt * 3);
        corAlvo.setHex(cfg.cor);
        corAtual.lerp(corAlvo, k);
        brilho = lerp(brilho, cfg.brilho, k);
        giro = lerp(giro, cfg.giro, k);
        aneis = lerp(aneis, cfg.aneis, k);
        const mov = reduzMov ? 0.3 : 1;

        for (const m of tintaveis) {
            m.color.copy(corAtual);
            m.opacity = Math.min(1, m.userData.op * brilho);
        }

        /* cérebro */
        cerebro.rotation.y += dt * giro * mov;
        cerebro.rotation.x = Math.sin(t * 0.3) * 0.12;
        cerebro.scale.setScalar(1 + Math.sin(t * 1.6) * 0.012 + amp * 0.09 * cfg.pulso);
        halo.scale.setScalar(6 + amp * 2.2 + Math.sin(t * 2) * 0.2);
        casca1.rotation.y -= dt * 0.15 * mov;
        casca1.rotation.x += dt * 0.07 * mov;
        casca2.rotation.y += dt * 0.03 * mov;

        /* pulsos nas sinapses */
        const vel = 0.4 + cfg.pulso * 2 + amp * 2;
        for (let i = 0; i < NP; i++) {
            const p = pulsos[i];
            p.t += dt * p.v * vel;
            if (p.t >= 1) novoPulso(p, p.to);
            tmpV.copy(nosPos[p.from]).lerp(nosPos[p.to], p.t).toArray(pulsoArr, i * 3);
        }
        pulsoGeo.attributes.position.needsUpdate = true;

        /* anéis, satélites, hologramas */
        const fa = aneis * mov;
        for (const [o, vx, vy, vz] of girantes) {
            o.rotation.x += vx * dt * fa;
            o.rotation.y += vy * dt * fa;
            o.rotation.z += vz * dt * fa;
        }

        /* espectro circular */
        for (let i = 0; i < NB; i++) {
            const a = (i / NB) * TAU;
            const f = (0.5 + 0.5 * Math.sin(t * 5 + i * 0.8)) * (0.5 + 0.5 * Math.sin(t * 2.3 - i * 0.37));
            const l = 0.05 + amp * (0.12 + 0.6 * f);
            const c = Math.cos(a), s = Math.sin(a), r0 = 2.5;
            espArr[i * 6]     = c * r0;       espArr[i * 6 + 1] = s * r0;       espArr[i * 6 + 2] = 0;
            espArr[i * 6 + 3] = c * (r0 + l); espArr[i * 6 + 4] = s * (r0 + l); espArr[i * 6 + 5] = 0;
        }
        espGeo.attributes.position.needsUpdate = true;

        /* ambiente */
        poeira.rotation.y += dt * 0.01 * mov;
        chao.position.z = (t * 0.8 * mov) % 2;
        teto.position.z = chao.position.z;

        /* câmera com parallax suave */
        camera.position.x = lerp(camera.position.x, mouse.x * 1.2, 0.03);
        camera.position.y = lerp(camera.position.y, 0.8 + mouse.y * 0.6, 0.03);
        camera.lookAt(0, 0.6, 0);

        renderer.render(scene, camera);
    }

    return { atualizar, redimensionar, aplicarQualidade };
}

/* =====================================================================
   CAMADAS 2D: onda
   ===================================================================== */
function criarOnda() {
    const c = $('onda'), g = c.getContext('2d');
    let w = 0, h = 0, acum = 0;
    function redim() { w = c.width = c.clientWidth; h = c.height = c.clientHeight; }
    function desenhar(dt, t, amp) {
        acum += dt;
        if (acum < 1 / 30) return;
        acum = 0;
        g.clearRect(0, 0, w, h);
        const n = Math.floor(w / 6);
        g.fillStyle = 'rgba(0,255,102,0.35)';
        for (let i = 0; i < n; i++) {
            const env = Math.sin((i / n) * Math.PI);
            const v = (0.5 + 0.5 * Math.sin(t * 6 + i * 0.5)) * (0.5 + 0.5 * Math.sin(t * 2.7 - i * 0.23));
            const bh = 2 + (amp * 0.9 + 0.04) * h * 0.9 * env * v;
            g.fillRect(i * 6, h / 2 - bh / 2, 3, bh);
        }
        g.beginPath();
        g.strokeStyle = '#00ff66';
        g.lineWidth = 1.5;
        for (let x = 0; x <= w; x += 3) {
            const y = h / 2
                + Math.sin(x * 0.03 + t * 5) * h * 0.35 * amp * Math.sin((x / w) * Math.PI)
                + Math.sin(x * 0.09 - t * 3) * h * 0.1 * amp;
            if (x === 0) g.moveTo(x, y); else g.lineTo(x, y);
        }
        g.stroke();
    }
    return { redim, desenhar };
}

/* =====================================================================
   ESTADO, LOG E MÉTRICAS
   ===================================================================== */
let estado = 'offline';
let cfg = ESTADOS.offline;
let amp = 0;

let ws = null, wsAberto = false, wsDesde = 0, tentativas = 0;
let tProc = 0, ultimaLat = 0, somaLat = 0, turnos = 0;

function definirEstado(nome) {
    if (nome === estado) return;
    estado = nome;
    cfg = ESTADOS[nome];
    el.estado.textContent = cfg.rotulo;
    el.estado.classList.remove('troca');
    void el.estado.offsetWidth;
    el.estado.classList.add('troca');
    document.body.dataset.estado = nome;
    document.body.classList.toggle('off', nome === 'offline');
}

const MAX_LOG = 8;
let ultimaEntrada = null, ultimoEstadoLog = null;
function registrar(nome, texto, forcarNovo) {
    const t = texto.length > 160 ? texto.slice(0, 157) + '…' : texto;
    if (!forcarNovo && ultimaEntrada && ultimoEstadoLog === nome) {
        ultimaEntrada.textContent = t;
        return;
    }
    const li = document.createElement('li');
    li.className = nome;
    const tm = document.createElement('time');
    tm.textContent = new Date().toLocaleTimeString('pt-BR');
    const sp = document.createElement('span');
    sp.textContent = t;
    li.append(tm, sp);
    el.log.prepend(li);
    while (el.log.children.length > MAX_LOG) el.log.lastChild.remove();
    ultimaEntrada = sp;
    ultimoEstadoLog = nome;
}

function mostrarMensagem(texto) {
    el.msg.textContent = texto;
    el.msg.scrollTop = el.msg.scrollHeight;
}

function aplicar(d) {
    const nome = ESTADOS[d.estado] && d.estado !== 'offline' ? d.estado : 'pronto';
    const msg = String(d.mensagem == null ? '' : d.mensagem);
    const agora = performance.now();

    if (nome === 'processando') tProc = agora;
    if (nome === 'respondendo' && tProc) {
        ultimaLat = agora - tProc;
        somaLat += ultimaLat;
        turnos++;
        tProc = 0;
    }
    definirEstado(nome);
    mostrarMensagem(msg);
    registrar(nome, msg);
}

/* ---------- WebSocket (com reconexão) ---------- */
function conectar() {
    const http = location.protocol === 'http:' || location.protocol === 'https:';
    const host = http && location.host ? location.host : 'localhost:8000';
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(proto + '://' + host + '/ws');

    ws.onopen = () => {
        wsAberto = true;
        wsDesde = performance.now();
        tentativas = 0;
        el.conexao.textContent = 'ENLACE ATIVO';
        definirEstado('pronto');
        mostrarMensagem('Enlace estabelecido. Aguardando o núcleo...');
        tentarFecharBoot();
    };
    ws.onmessage = (e) => {
        let d;
        try { d = JSON.parse(e.data); } catch (_) { return; }
        aplicar(d);
    };
    ws.onclose = () => {
        wsAberto = false;
        el.conexao.textContent = 'SEM ENLACE';
        definirEstado('offline');
        mostrarMensagem('SEM CONEXÃO COM O NÚCLEO. TENTANDO NOVAMENTE...');
        registrar('sistema', 'Conexão perdida. Reconectando...', true);
        setTimeout(conectar, Math.min(5000, 800 + tentativas++ * 500));
    };
    ws.onerror = () => { try { ws.close(); } catch (_) { /* já fechado */ } };
}

/* ---------- boot ---------- */
const LINHAS_BOOT = [
    'C.Y.N.I.C. // INICIALIZANDO NÚCLEO',
    'CARREGANDO MÓDULO NEURAL ............ OK',
    'CALIBRANDO CANAL DE ÁUDIO ........... OK',
    'SINTETIZADOR DE VOZ ................. OK',
    'ESTABELECENDO ENLACE COM O SERVIDOR ...'
];
let bootTerminou = false, bootFechado = false;
function fecharBoot() {
    if (bootFechado || !el.boot) return;
    bootFechado = true;
    el.boot.classList.add('fim');
    setTimeout(() => el.boot.remove(), 900);
}
function tentarFecharBoot() { if (bootTerminou && wsAberto) fecharBoot(); }
function iniciarBoot() {
    let i = 0;
    const passo = () => {
        if (i < LINHAS_BOOT.length) {
            const d = document.createElement('div');
            d.textContent = LINHAS_BOOT[i++];
            el.bootLinhas.appendChild(d);
            setTimeout(passo, reduzMov ? 60 : 260);
        } else {
            bootTerminou = true;
            tentarFecharBoot();
        }
    };
    passo();
    setTimeout(fecharBoot, 4500);
    el.boot.addEventListener('click', fecharBoot);
}

/* ---------- microfone (opcional: onda real) ---------- */
let micAtivo = false, micStream = null, micCtx = null, analisador = null, bufMic = null, nivelMic = 0;
async function alternarMic() {
    if (micAtivo) {
        micStream.getTracks().forEach((t) => t.stop());
        if (micCtx) micCtx.close();
        micAtivo = false; analisador = null; nivelMic = 0;
        atualizarDicas();
        return;
    }
    try {
        micStream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false } });
        micCtx = new (window.AudioContext || window.webkitAudioContext)();
        const src = micCtx.createMediaStreamSource(micStream);
        analisador = micCtx.createAnalyser();
        analisador.fftSize = 512;
        src.connect(analisador);
        bufMic = new Uint8Array(analisador.fftSize);
        micAtivo = true;
    } catch (err) {
        micAtivo = false;
        registrar('sistema', 'Microfone indisponível: ' + (err && err.name ? err.name : 'erro'), true);
    }
    atualizarDicas();
}
function lerMic() {
    analisador.getByteTimeDomainData(bufMic);
    let s = 0;
    for (let i = 0; i < bufMic.length; i++) { const d = (bufMic[i] - 128) / 128; s += d * d; }
    nivelMic = clamp(Math.sqrt(s / bufMic.length) * 6, 0, 1);
}

/* ---------- amplitude (voz simulada ou real) ---------- */
function calcularAmp(dt, t) {
    let alvo = 0.04;
    if (micAtivo && analisador) {
        lerMic();
        alvo = nivelMic;
    } else if (estado === 'respondendo') {
        alvo = 0.3 + 0.7 * Math.abs(Math.sin(t * 7.3) * Math.sin(t * 2.1 + 1)) * (0.6 + 0.4 * Math.random());
    } else if (estado === 'ouvindo') {
        alvo = 0.08 + 0.05 * Math.sin(t * 2);
    } else if (estado === 'processando') {
        alvo = 0.2 + 0.1 * Math.sin(t * 12);
    }
    amp = lerp(amp, alvo, 1 - Math.exp(-dt * 12));
}

/* ---------- teclas e botões ---------- */
function atualizarDicas() {
    el.btnQ.textContent = '[Q] Qualidade: ' + QUALIDADES[qualidade].nome;
    el.btnM.textContent = '[M] Microfone: ' + (micAtivo ? 'ON' : 'OFF');
}
function mudarQualidade(q, auto) {
    qualidade = q;
    try { localStorage.setItem('cynic-q', String(q)); } catch (_) { /* ok */ }
    if (cena) cena.aplicarQualidade(q);
    atualizarDicas();
    if (auto) registrar('sistema', 'FPS baixo: qualidade reduzida para ' + QUALIDADES[q].nome + '.', true);
}
function telaCheia() {
    if (document.fullscreenElement) document.exitFullscreen();
    else document.documentElement.requestFullscreen().catch(() => {});
}
window.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const k = e.key.toLowerCase();
    if (k === 'q') mudarQualidade((qualidade + 2) % 3);
    else if (k === 'm') alternarMic();
    else if (k === 'f') telaCheia();
});
el.btnQ.addEventListener('click', () => mudarQualidade((qualidade + 2) % 3));
el.btnM.addEventListener('click', alternarMic);
el.btnF.addEventListener('click', telaCheia);

/* =====================================================================
   INICIALIZAÇÃO E LOOP PRINCIPAL
   ===================================================================== */
const onda = criarOnda();
let cena = null;

if (typeof THREE !== 'undefined') {
    try {
        cena = criarCena();
        cena.aplicarQualidade(qualidade);
    } catch (err) {
        cena = null;
        registrar('sistema', 'WebGL indisponível: ' + err.message, true);
    }
} else {
    registrar('sistema', 'Three.js não carregou (sem internet?). Rodando só o HUD.', true);
}

function redimensionarTudo() {
    if (cena) cena.redimensionar();
    onda.redim();
}
window.addEventListener('resize', redimensionarTudo);
redimensionarTudo();
atualizarDicas();
definirEstado('offline');
iniciarBoot();
conectar();

/* relógio e uptime */
function tickRelogio() {
    const d = new Date();
    el.relogio.textContent = pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
    el.data.textContent = pad(d.getDate()) + '/' + pad(d.getMonth() + 1) + '/' + d.getFullYear();
    if (wsAberto) {
        const s = Math.floor((performance.now() - wsDesde) / 1000);
        el.up.textContent = pad(Math.floor(s / 3600)) + ':' + pad(Math.floor((s % 3600) / 60)) + ':' + pad(s % 60);
    }
}
setInterval(tickRelogio, 1000);
tickRelogio();

/* loop */
let tAnterior = performance.now(), tempo = 0;
let quadros = 0, tFps = performance.now(), fps = 0, lentos = 0, tBarras = 0;
const inicioApp = performance.now();

document.addEventListener('visibilitychange', () => { tFps = performance.now(); quadros = 0; tAnterior = performance.now(); });

function loop(agora) {
    requestAnimationFrame(loop);
    const dt = Math.min(0.05, (agora - tAnterior) / 1000);
    tAnterior = agora;
    tempo += dt;

    calcularAmp(dt, tempo);
    if (cena) cena.atualizar(dt, tempo, cfg, amp);
    onda.desenhar(dt, tempo, amp);

    /* barras e métricas (~2x por segundo) */
    tBarras += dt;
    if (tBarras > 0.12) {
        tBarras = 0;
        el.bNucleo.style.transform = 'scaleX(' + clamp(cfg.brilho / 1.5, 0.05, 1).toFixed(2) + ')';
        el.bSinapses.style.transform = 'scaleX(' + clamp(0.15 + cfg.pulso * 0.5 + amp * 0.35 + Math.random() * 0.08, 0.05, 1).toFixed(2) + ')';
        el.bFluxo.style.transform = 'scaleX(' + clamp(0.05 + amp, 0.05, 1).toFixed(2) + ')';
    }

    quadros++;
    if (agora - tFps >= 500) {
        fps = (quadros * 1000) / (agora - tFps);
        quadros = 0;
        tFps = agora;
        el.fps.textContent = Math.round(fps);
        el.mem.textContent = performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) + ' MB' : 'n/d';
        el.lat.textContent = ultimaLat ? (ultimaLat / 1000).toFixed(2) + ' s' : '--';
        el.med.textContent = turnos ? (somaLat / turnos / 1000).toFixed(2) + ' s' : '--';
        el.turnos.textContent = turnos;

        /* qualidade automática: só desce, e só depois do aquecimento */
        if (agora - inicioApp > 5000 && qualidade > 0) {
            lentos = fps < 28 ? lentos + 1 : 0;
            if (lentos >= 6) { lentos = 0; mudarQualidade(qualidade - 1, true); }
        }
    }
}
requestAnimationFrame(loop);

})();
