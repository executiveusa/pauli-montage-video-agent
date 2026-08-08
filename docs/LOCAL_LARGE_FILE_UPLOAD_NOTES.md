# Local large-file transfer boundary

Montage's current browser-to-worker media path is suitable for large local source files because the media request is sent directly from the browser to the loopback worker, not through the hosted Next/Vercel application.

Current boundary:

- browser control surface: `https://pauli-montage-video-agent.vercel.app`;
- local worker: `http://127.0.0.1:4788`;
- upload endpoint: `POST /assets`;
- media request body: browser `File` object;
- worker storage: configured `MONTAGE_LOCAL_WORKSPACE`;
- worker copy loop: bounded chunks until `Content-Length` is satisfied;
- source media: immutable after registration;
- hosted application: does not proxy or store the video bytes.

For the ASC3ND proof the default workspace is `E:\MONTAGE_MEDIA`, avoiding consumption of the Windows system drive.

The current MVP intentionally copies the chosen file into the project workspace. Do not add arbitrary browser-supplied filesystem paths merely to avoid that copy. An approved-root/link mode can be added later with an explicit local trust contract after Phase 3 is proven.
