m# Pehle yeh parhein — Computer A / Computer B Setup

## 1) Dono Windows EXE banayein

1. Project ko kisi Windows 10/11 **64-bit** computer par extract karein.
2. Us build computer par Python **3.11 64-bit** install karein (Add Python to PATH / Python Launcher enabled ho).
3. Project folder mein `BUILD_WINDOWS.bat` par double-click karein.
4. Build complete hone ke baad `release` folder mein yeh do files hon gi:
   - `ComputerA_Client.exe` — sirf Computer A par copy karein.
   - `ComputerB_Server.exe` — sirf Computer B par copy karein.
5. Build ho jane ke baad target computers par Python install karna zaroori nahi; EXEs one-file PyInstaller builds hain.

> Is delivered archive mein Windows EXEs pehle se bundled nahi hain. Current build environment Linux hai, is liye yahan native Windows EXE compile nahi ki ja sakti. EXEs Windows build step par generate hon gi.

## 2) Network connect karein

### Direct Ethernet cable (recommended dedicated link)

- Computer B par `setup_lan_ip_server.bat` ko **Run as administrator** karein: IP `192.168.1.20`.
- Computer A par `setup_lan_ip_client.bat` ko **Run as administrator** karein: IP `192.168.1.10`.
- Yeh scripts Ethernet adapter ka static IP badalti hain. Agar adapter ka naam `Ethernet` nahi hai to Windows `ncpa.cpl` mein adapter name check karein aur script update karein.
- Agar dono PCs same Wi-Fi/router par hain to in static-IP scripts ko **mat** chalayein. Router DHCP rehne dein; Server dashboard ka actual LAN IP use karein.

## 3) Computer B — Rendering Server

1. `ComputerB_Server.exe` run karein.
2. Windows Firewall prompt aaye to Private network par allow karein.
3. Dashboard mein **Start Server** click karein.
4. Dashboard par LAN IP aur GPU/NVENC status dekhein. Server TCP port `5000` aur LAN discovery UDP port `5005` use karta hai.

## 4) Computer A — Client

1. `ComputerA_Client.exe` run karein.
2. Server IP `192.168.1.20` (direct cable) ya Computer B ka actual Wi-Fi/LAN IP enter karein.
3. Port `5000` rakhein.
4. **Handshake & Ping** click karein. Status `ONLINE` hona chahiye.

## 5) CapCut ki poori editable timeline Computer B par chalana

1. Dono computers par **CapCut Desktop** install karein. B par A wala hi CapCut version/build rakhna behtar hai. Account/region gated effects ke liye B par required account sign-in bhi karein.
2. Dono computers par CapCut completely close karein. A par project Save karne ke baad editor close karein; B par bhi CapCut close rakhein jab tak transfer complete na ho.
3. Computer B par `ComputerB_Server.exe` → **Start Server** karein. Computer A par `ComputerA_Client.exe` khol kar Handshake & Ping se B connect karein.
4. Client ke **CapCut Timeline Handoff & Export Watch** tab mein right side `Full Editable CapCut Timeline Handoff` se project select karein.
5. **Send Full Editable Timeline to B & Open CapCut** click karein. Full draft folder, readable JSON mein milne wali local media files, project assets aur metadata B par transfer honge. File transfer SHA-256 se verify hota hai. B par media paths rewrite honge aur CapCut draft index ka backup bana kar project register kiya jayega.
6. B par CapCut Home/Projects mein transferred project select karein. Missing assets ya effects ko check karein; phir **CapCut ke andar Computer B par Export click karein**. Is export mein CapCut khud original tracks, effects, titles, transitions aur audio mix render karega.
7. Rendered MP4 ko A par lane ke liye B ke **LAN File Sharing Hub → Share Local File to Hub** se export file select karein. Phir A ke **LAN File Sharing Hub → Refresh Server Files → Download from Server** se MP4 download karein.

**Important:** A-side application ka `Send Full Editable Timeline` button project ko B par bhejta aur CapCut kholta hai. Yeh CapCut ke apne native Export button on A ko intercept nahi karta. CapCut ka public headless render API/CLI available nahi hai; is liye actual Export click B ki visible CapCut window mein karna hota hai. CapCut ki internal draft format undocumented/version-dependent hai. Default Windows draft folder use hota hai; custom CapCut Draft Save location ho to pehle B par default location set karein. Local files ke saath transfer hota hai, lekin cloud-only assets, region/account gated effects aur missing system fonts B par re-download/fallback maang sakte hain. Transfer behavior ko real CapCut installation par verify karna zaroori hai.

## 6) Purana MP4 Export Watcher (Optional)

Left-side **Completed Export Watcher** ab bhi alag optional workflow hai: A par CapCut se MP4 export karein, watcher completed file detect karega aur B par FFmpeg second-pass re-encode karega. Yeh full editable timeline workflow nahi hai. Is path mein CapCut ka initial render A par hi hota hai.

Final files (EXE mode):

`%LOCALAPPDATA%\CSC334\Client\client_downloads\`

## 7) NVIDIA GPU

Computer B par NVIDIA GPU + supported NVIDIA driver aur NVENC-enabled FFmpeg hona chahiye. FFmpeg `PATH` mein ho ya `FFMPEG_PATH` environment variable se uska exact executable set karein. Server dashboard actual NVENC probe status batata hai. Agar probe/driver fail ho to system CPU `libx264` fallback use karega; GPU encoding ka jhoota status nahi dikhaya jayega.

---

## Troubleshooting

- **Client connect nahi hota:** Computer B par Server dashboard mein Start Server check karein; IP aur port check karein; Windows Firewall mein TCP 5000 aur UDP 5005 allow karein.
- **Watcher kuch nahi karta:** CapCut ka actual export folder select karein, watcher ko export se pehle activate karein, aur exported video extension supported honi chahiye (MP4/MOV/MKV/AVI/WebM/WMV/FLV/M4V/TS).
- **GPU active nahi:** Server dashboard ka NVENC status dekhein; FFmpeg ke `PATH`/`FFMPEG_PATH` aur NVIDIA driver verify karein. CPU fallback expected behavior hai jab NVENC available na ho.
- **Output nahi milta:** Client ke `client_downloads` folder mein `logs.txt` aur server render log dekhein.
