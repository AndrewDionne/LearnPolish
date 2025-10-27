(function(w){
  const APP = w.APP_CONFIG || {};
  function sanitize(t){return (t||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-zA-Z0-9_-]+/g,"_").replace(/^_+|_+$/g,"");}
  async function fetchManifest(setName){
    const probes = [
      `../../static/${encodeURIComponent(setName)}/r2_manifest.json`,
      `../../static/r2_manifest.json`
    ];
    for (const u of probes){
      try{ const r = await fetch(u,{cache:"no-store"}); if(r.ok) return await r.json(); }catch(e){}
    }
    return null;
  }
  function buildAudioPath(setName, index, item, manifest){
    const fn = (item && item.audio_file) ? String(item.audio_file)
              : `${index}_${sanitize(item?.phrase||item?.polish||"")}.mp3`;
    const key = `audio/${setName}/${fn}`;
    if (manifest?.files?.[key]) return manifest.files[key];
    const base = manifest?.assetsBase || manifest?.cdn || manifest?.base || APP.assetsBase;
    if (base) return String(base).replace(/\/$/,"") + "/" + key;
    return `../../static/${encodeURIComponent(setName)}/audio/${encodeURIComponent(fn)}`;
  }
  w.AudioPaths = { fetchManifest, buildAudioPath };
})(window);
