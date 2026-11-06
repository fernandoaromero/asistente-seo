let idProyectoActual = null;
let guionOriginal = "";
let quill = null;
let configGlobal = { topicos: [], canales: [], videos_por_topico: 1, meses_antiguedad: 3 };
let videoIdManual = null;

document.addEventListener('DOMContentLoaded', () => {
    quill = new Quill('#editor-container', {
        theme: 'snow',
        placeholder: 'Escribe tu guión aquí...',
        modules: {
            toolbar: [
                [{ 'header': [1, 2, 3, false] }],
                ['bold', 'italic', 'underline', 'strike'],
                [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                ['link', 'blockquote', 'code-block'],
                ['clean']
            ]
        }
    });

    cargarProduccion();
});

function cambiarTab(idTab, elementoTab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.container').forEach(c => c.classList.remove('active'));
    elementoTab.classList.add('active');
    document.getElementById('tab-' + idTab).classList.add('active');
    
    if (idTab === 'config') cargarConfiguracion();
    if (idTab === 'produccion') cargarProduccion();
    if (idTab === 'publicados') cargarPublicados();
}

function cargarProduccion() {
    fetch('/api/produccion')
        .then(res => res.json())
        .then(proyectos => {
            const grid = document.getElementById('grid-produccion');
            grid.innerHTML = ""; 
            
            if (proyectos.length === 0) {
                grid.innerHTML = "<p style='color: var(--text-muted);'>No hay proyectos en producción.</p>";
                return;
            }

            proyectos.forEach(p => {
                const card = document.createElement('div');
                card.className = 'card';
                card.id = `card-${p.id}`;
                
                let botonAccion = '';
                if (p.estado === 'pendiente') {
                    botonAccion = `<button class="btn-action btn-upload" style="background:var(--accent); color:#fff;" onclick="generarSEO(${p.id}, this)">⚡ Generar SEO</button>`;
                } else if (p.trio_listo) {
                    botonAccion = `<button class="btn-action btn-upload" onclick="subirVideo(${p.id}, this)">📤 Subir</button>`;
                } else {
                    botonAccion = `<button class="btn-action btn-play" style="cursor:not-allowed; opacity:0.5;" title="Falta el video .mp4 o la miniatura .png">⏳ Esperando archivos</button>`;
                }

                card.innerHTML = `
                    <button class="btn-delete-card" onclick="eliminarProyecto(${p.id}, '${p.titulo.replace(/'/g, "\\'")}')" title="Eliminar">🗑️</button>
                    <div>
                        <div class="card-header">
                            <h3 class="card-title" onclick="abrirDetalle(${p.id})">${p.titulo}</h3>
                        </div>
                        ${p.estado === 'pendiente' 
                            ? '<span class="badge badge-pending">Pendiente</span>' 
                            : (p.trio_listo ? '<span class="badge badge-ready" style="background:var(--green); color:#000;">Listo para Subir</span>' : '<span class="badge badge-ready">En Edición</span>')}
                        <div class="card-meta" style="margin-top: 10px;">Aprobado el: ${p.fecha_creacion}</div>
                    </div>
                    <div class="card-actions">
                        <button class="btn-action btn-play" onclick="abrirVideo('${p.video_id_inspiracion}')">▶ Inspiración</button>
                        <button class="btn-action btn-details" onclick="abrirDetalle(${p.id})">📝 Guión</button>
                        ${botonAccion}
                    </div>
                `;
                grid.appendChild(card);
            });
        });
}

function cargarPublicados() {
    fetch('/api/publicados')
        .then(res => res.json())
        .then(proyectos => {
            const grid = document.getElementById('grid-publicados');
            grid.innerHTML = ""; 
            
            if (proyectos.length === 0) {
                grid.innerHTML = "<p style='color: var(--text-muted);'>Aún no has publicado ningún video.</p>";
                return;
            }

            proyectos.forEach(p => {
                const card = document.createElement('div');
                card.className = 'card published';
                card.innerHTML = `
                    <div>
                        <div class="card-header">
                            <h3 class="card-title" style="color: var(--text-muted);">${p.titulo}</h3>
                        </div>
                        <span class="badge badge-published">Publicado</span>
                        <div class="card-meta" style="margin-top: 10px;">Subido el: ${p.fecha_publicacion}</div>
                    </div>
                    <div class="card-actions" style="border-top-color: rgba(46, 204, 113, 0.3);">
                        <a href="https://youtube.com/watch?v=${p.video_id_youtube}" target="_blank" class="btn-action btn-yt-link">▶ Ver en YouTube</a>
                        <button class="btn-action btn-details" onclick="revertirPublicacion(${p.id})" title="Devolver a Producción">↩️ Revertir</button>
                    </div>
                `;
                grid.appendChild(card);
            });
        });
}

// --- NUEVA FUNCIÓN: REVERTIR PUBLICACIÓN ---
function revertirPublicacion(id) {
    if (!confirm("⚠️ ¿Estás seguro de devolver este proyecto a Producción?\n\n(Nota: El video NO se borrará de YouTube, deberás borrarlo tú manualmente desde YouTube Studio).")) return;

    fetch(`/api/proyecto/${id}/revertir`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            alert("✅ " + data.mensaje);
            cargarPublicados(); // Recargamos la lista de publicados
        })
        .catch(() => alert("Error al conectar con el servidor."));
}

function subirVideo(id, boton) {
    if(!confirm("¿Subir este video a YouTube como PRIVADO y mover los archivos a 'B. Publicados'?")) return;
    
    const textoOriginal = boton.innerText;
    boton.innerText = "⏳ Subiendo...";
    boton.disabled = true;

    fetch(`/api/proyecto/${id}/subir`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if(data.error) {
                alert("❌ " + data.error);
                boton.innerText = textoOriginal;
                boton.disabled = false;
                return;
            }
            alert("🎉 " + data.mensaje);
            cargarProduccion();
        })
        .catch(() => {
            alert("Error crítico al conectar con el servidor.");
            boton.innerText = textoOriginal;
            boton.disabled = false;
        });
}

function abrirModalManual() {
    document.getElementById('modalManual').style.display = 'flex';
    document.getElementById('input-url-manual').value = "";
    document.getElementById('input-titulo-manual').value = "";
    document.getElementById('feedback-url').style.display = 'none';
    videoIdManual = null;
}

function cerrarModalManual() {
    document.getElementById('modalManual').style.display = 'none';
}

function autodetectarUrl() {
    const url = document.getElementById('input-url-manual').value.trim();
    const feedback = document.getElementById('feedback-url');
    const inputTitulo = document.getElementById('input-titulo-manual');
    
    if (!url.includes('youtube.com') && !url.includes('youtu.be')) {
        feedback.style.display = 'none';
        return;
    }

    feedback.style.display = 'block';
    feedback.style.color = 'var(--text-muted)';
    feedback.innerText = "🔍 Detectando título...";
    inputTitulo.placeholder = "Cargando título del video...";

    fetch('/api/detectar_link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            feedback.style.color = 'var(--red)';
            feedback.innerText = "⚠️ " + data.error;
            inputTitulo.placeholder = "Escribe el título manualmente";
            videoIdManual = null;
        } else {
            feedback.style.color = 'var(--green)';
            feedback.innerText = "✅ Título detectado automáticamente.";
            inputTitulo.value = data.titulo;
            videoIdManual = data.video_id;
        }
    })
    .catch(() => {
        feedback.style.color = 'var(--red)';
        feedback.innerText = "⚠️ Error al conectar con el servidor.";
    });
}

function guardarIdeaManual() {
    const titulo = document.getElementById('input-titulo-manual').value.trim();
    if (!titulo) { alert("⚠️ Escribe un título o pega un link."); return; }

    fetch('/api/proyecto/crear_manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ titulo: titulo, video_id: videoIdManual })
    }).then(res => res.json()).then(data => {
        if (data.error) { alert(data.error); return; }
        cerrarModalManual();
        cargarProduccion();
    });
}

function generarSEO(id, boton) {
    if(!confirm("¿Generar SEO con Gemini y crear la carpeta del proyecto?")) return;
    const textoOriginal = boton.innerText;
    boton.innerText = "⏳ Generando...";
    boton.disabled = true;

    fetch(`/api/proyecto/${id}/generar_seo`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if(data.error) {
                alert(data.error);
                boton.innerText = textoOriginal;
                boton.disabled = false;
                return;
            }
            alert("✅ " + data.mensaje);
            cargarProduccion();
        })
        .catch(() => {
            alert("Error al conectar con el servidor.");
            boton.innerText = textoOriginal;
            boton.disabled = false;
        });
}

function abrirDetalle(id) {
    idProyectoActual = id;
    document.getElementById('modalDetalle').style.display = 'flex'; 
    document.getElementById('modal-titulo').innerText = "Cargando...";
    quill.setContents([]);
    
    fetch(`/api/proyecto/${id}`)
        .then(res => res.json())
        .then(data => {
            if(data.error) return alert("Error al cargar");
            document.getElementById('modal-titulo').innerText = data.titulo;
            
            const bloqueViral = document.getElementById('bloque-titulo-viral');
            const inputViral = document.getElementById('modal-titulo-viral-input');
            
            if (data.estado !== 'pendiente' && data.titulo_viral) {
                bloqueViral.style.display = 'block';
                inputViral.value = data.titulo_viral;
            } else {
                bloqueViral.style.display = 'none';
            }

            document.getElementById('modal-desc').innerText = data.seo_descripcion || "Sin descripción.";
            document.getElementById('modal-tags').innerText = data.seo_tags || "Sin tags.";
            document.getElementById('modal-gancho').innerText = data.seo_gancho || "Sin gancho.";
            
            if (data.guion) quill.clipboard.dangerouslyPasteHTML(data.guion);
            guionOriginal = data.guion || "";
            
            const btnSeoModal = document.getElementById('btn-generar-seo-modal');
            if (data.estado === 'pendiente') {
                btnSeoModal.style.display = 'block';
                btnSeoModal.onclick = () => { cerrarModal(); generarSEO(id, btnSeoModal); };
            } else {
                btnSeoModal.style.display = 'none';
            }
        });
}

function guardarTituloViral(event) {
    if (!idProyectoActual) return;
    const nuevoTitulo = document.getElementById('modal-titulo-viral-input').value;
    const btn = event.target;
    
    fetch(`/api/proyecto/${idProyectoActual}/guardar_titulo`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ titulo_viral: nuevoTitulo })
    }).then(() => {
        btn.innerText = "✅ Guardado";
        setTimeout(() => btn.innerText = "Guardar", 2000);
    });
}

function cerrarModal() {
    if (!idProyectoActual) return;
    const guionActual = quill.root.innerHTML;
    const guionNormalizado = (guionActual === "<p><br></p>") ? "" : guionActual;
    const originalNormalizado = (guionOriginal === "<p><br></p>") ? "" : guionOriginal;

    if (guionNormalizado !== originalNormalizado) {
        if (!confirm("⚠️ Tienes cambios sin guardar en el guión.\n\n¿Seguro que quieres salir?")) return;
    }
    document.getElementById('modalDetalle').style.display = 'none'; 
    idProyectoActual = null;
    guionOriginal = "";
}

document.getElementById('btn-guardar-guion').addEventListener('click', function() {
    if (!idProyectoActual) return;
    const textoGuion = quill.root.innerHTML;
    const boton = this;
    boton.innerText = "Guardando..."; boton.disabled = true;

    fetch(`/api/proyecto/${idProyectoActual}/guardar_guion`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ guion: textoGuion })
    }).then(() => {
        boton.innerText = "💾 Guardar Guión"; boton.disabled = false;
        guionOriginal = textoGuion; 
        boton.style.backgroundColor = "var(--green)";
        setTimeout(() => boton.style.backgroundColor = "var(--accent)", 2000);
    });
});

function eliminarProyecto(id, titulo) {
    if (!confirm(`¿Eliminar "${titulo}"?\n\nEsto borrará la carpeta en A. Producción.`)) return;
    fetch(`/api/proyecto/${id}`, { method: 'DELETE' }).then(() => {
        cerrarModal();
        cargarProduccion();
    });
}

document.getElementById('btn-eliminar-modal').addEventListener('click', () => {
    if(idProyectoActual) eliminarProyecto(idProyectoActual, document.getElementById('modal-titulo').innerText);
});

window.addEventListener('click', (event) => { 
    if (event.target === document.getElementById('modalDetalle')) cerrarModal(); 
    if (event.target === document.getElementById('modalManual')) cerrarModalManual();
});
document.addEventListener('keydown', (event) => { 
    if (event.key === "Escape") { cerrarModal(); cerrarModalManual(); }
});

function abrirVideo(videoId) {
    if (!videoId || videoId === 'None' || videoId === 'null') {
        alert("Este proyecto no tiene un video de inspiración.");
        return;
    }
    document.getElementById('iframe-video').src = `https://www.youtube.com/embed/${videoId}?autoplay=1`;
    document.getElementById('modalVideo').style.display = 'flex';
}

function cerrarVideoModal(event) {
    if (event && event.target !== event.currentTarget && event.target.tagName !== 'BUTTON') return;
    document.getElementById('modalVideo').style.display = 'none';
    document.getElementById('iframe-video').src = '';
}

function buscarTendencias() {
    const btn = document.getElementById('btn-buscar');
    const spinner = document.getElementById('loading-tendencias');
    const grid = document.getElementById('grid-explorar');

    btn.disabled = true; btn.innerText = "Buscando..."; grid.innerHTML = ""; spinner.style.display = 'block';

    fetch('/api/explorar')
        .then(res => res.json())
        .then(data => {
            spinner.style.display = 'none'; btn.disabled = false; btn.innerText = "🚀 Buscar Tendencias";
            
            if(data.length === 0) {
                grid.innerHTML = "<p style='color:var(--text-muted);'>No hay resultados nuevos.</p>";
                return;
            }

            data.forEach(video => {
                const card = document.createElement('div');
                card.className = 'card';
                card.id = `explorar-card-${video.video_id}`;
                
                const btnVer = video.video_id ? `<button class="btn-action btn-play" onclick="abrirVideo('${video.video_id}')">▶ Ver</button>` : '';

                card.innerHTML = `
                    <div>
                        <div class="card-header">
                            <h3 class="card-title" style="font-size: 16px;">${video.titulo}</h3>
                        </div>
                        <span class="badge badge-pending">${video.seed_origen}</span>
                        <div class="card-meta" style="margin-top: 10px; display: flex; flex-direction: column; gap: 5px;">
                            <span style="color: var(--text-muted); font-size: 12px;">Publicado ${video.fecha_texto || 'recientemente'}</span>
                            <span>Canal: ${video.canal} · <span style="color:var(--red); font-weight:bold;">${video.vistas_texto} vistas</span></span>
                        </div>
                    </div>
                    <div class="card-actions">
                        <button class="btn-explorar-action btn-discard-explore" onclick="descartarVideo('${video.video_id}', '${video.titulo.replace(/'/g, "\\'")}', this)">❌ Descartar</button>
                        <button class="btn-explorar-action btn-add-prod" onclick="añadirAProduccion('${video.titulo.replace(/'/g, "\\'")}', '${video.video_id}', this)">✅ Añadir</button>
                        ${btnVer}
                    </div>
                `;
                grid.appendChild(card);
            });
        })
        .catch(() => {
            alert("Error al buscar tendencias"); spinner.style.display = 'none'; btn.disabled = false; btn.innerText = "🚀 Buscar Tendencias";
        });
}

function añadirAProduccion(titulo, video_id, boton) {
    boton.innerText = "Añadiendo..."; boton.disabled = true;
    fetch('/api/proyecto/crear', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ titulo: titulo, video_id: video_id })
    }).then(() => {
        boton.innerText = "✅ Añadido"; boton.style.backgroundColor = "var(--green)"; boton.style.color = "#000";
        cargarProduccion();
    });
}

function descartarVideo(video_id, titulo, boton) {
    boton.innerText = "Descartado"; boton.disabled = true;
    fetch('/api/descartar', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ video_id: video_id, titulo: titulo })
    }).then(() => {
        const card = document.getElementById(`explorar-card-${video_id}`);
        if (card) card.style.display = 'none';
    });
}

function cargarConfiguracion() {
    fetch('/api/config')
        .then(res => res.json())
        .then(data => {
            configGlobal = data;
            
            const listaT = document.getElementById('lista-topicos');
            listaT.innerHTML = "";
            data.topicos.forEach(t => {
                listaT.innerHTML += `<div class="config-item"><span>${t.nombre}</span><button onclick="borrarTopico(${t.id})">🗑️</button></div>`;
            });

            const listaC = document.getElementById('lista-canales');
            listaC.innerHTML = "";
            data.canales.forEach(c => {
                listaC.innerHTML += `<div class="config-item"><span>@${c.handle}</span><button onclick="borrarCanal(${c.id})">🗑️</button></div>`;
            });

            document.getElementById('input-videos').value = data.videos_por_topico;
            document.getElementById('input-meses').value = data.meses_antiguedad;
            document.getElementById('input-api-key').value = data.gemini_api_key || "";
            actualizarTextoCalculo();
        });
}

function añadirTopico() {
    const input = document.getElementById('input-topico');
    if (!input.value.trim()) return;
    fetch('/api/config/topico', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nombre: input.value.trim() })
    }).then(res => {
        if(res.ok) { input.value = ""; cargarConfiguracion(); }
        else alert("El tópico ya existe.");
    });
}

function borrarTopico(id) {
    if(!confirm("¿Eliminar tópico?")) return;
    fetch(`/api/config/topico/${id}`, { method: 'DELETE' }).then(() => cargarConfiguracion());
}

function añadirCanal() {
    const input = document.getElementById('input-canal');
    if (!input.value.trim()) return;
    fetch('/api/config/canal', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ handle: input.value.trim() })
    }).then(res => {
        if(res.ok) { input.value = ""; cargarConfiguracion(); }
        else alert("El canal ya existe.");
    });
}

function borrarCanal(id) {
    if(!confirm("¿Eliminar canal?")) return;
    fetch(`/api/config/canal/${id}`, { method: 'DELETE' }).then(() => cargarConfiguracion());
}

function cambiarVideos(delta) {
    const input = document.getElementById('input-videos');
    let val = parseInt(input.value) + delta;
    if (val < 1) val = 1;
    if (val > 10) val = 10;
    input.value = val;
    guardarVideos();
}

function guardarVideos() {
    const val = document.getElementById('input-videos').value;
    fetch('/api/config/videos', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ videos: val })
    }).then(() => {
        configGlobal.videos_por_topico = parseInt(val);
        actualizarTextoCalculo();
    });
}

function cambiarMeses(delta) {
    const input = document.getElementById('input-meses');
    let val = parseInt(input.value) + delta;
    if (val < 1) val = 1;
    if (val > 12) val = 12;
    input.value = val;
    guardarMeses();
}

function guardarMeses() {
    const val = document.getElementById('input-meses').value;
    fetch('/api/config/meses', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ meses: val })
    }).then(() => {
        configGlobal.meses_antiguedad = parseInt(val);
        actualizarTextoCalculo();
    });
}

function guardarApiKey() {
    const key = document.getElementById('input-api-key').value.trim();
    fetch('/api/config/gemini_key', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ api_key: key })
    }).then(() => {
        alert("✅ API Key guardada correctamente.");
    });
}

function actualizarTextoCalculo() {
    const nTopicos = configGlobal.topicos.length;
    const vTopicos = configGlobal.videos_por_topico;
    const total = nTopicos * vTopicos;
    
    document.getElementById('texto-calculo').innerText = `Tienes ${nTopicos} tópicos configurados. Se mostrarán ${total} videos en total.`;
    document.getElementById('texto-calculo-meses').innerText = `Solo se mostrarán videos publicados en los últimos ${configGlobal.meses_antiguedad} meses.`;
}