# Anime Unity Downloader (Dockerized Web UI)
A full-stack, containerized application to download your favorite manga from Manga World with ease.  This project takes the powerful core logic of the original downloader and wraps it into a simple web interface, making it accessible even to those who aren't comfortable with the command line.  

 <img width="661" height="693" alt="Screenshot 2026-07-30 alle 13 08 47" src="https://github.com/user-attachments/assets/dbe9ac69-a32a-41cd-936f-057982acefc7" />

> [!IMPORTANT]
> This tool is for educational purposes only. Please respect the terms of service of the original platform and support the anime & manga industry by using official streaming services whenever possible.


# Credits & Attribution
The core backend logic of this application is heavily based on and inspired by the excellent work of Lysagxra/MangaWorldDowloader.  

I have extended the original project by:  
- Developing a dedicated Frontend for a better user experience.
- Refactoring the backend engine to output real-time download progress to a progress.json file, enabling dynamic progress bars in the UI.
- Fixed minor bugs.
- Dockerizing the entire workflow (Backend + Frontend) for portability.
- Optimizing the integration between the web UI and the download engine.

# Installation & Usage
Prerequisites:  
[Docker](https://www.docker.com) and [Docker Compose](https://docs.docker.com/compose/) installed on your system.

Create a ```docker-compose.yml``` file:
```
services:
  manga-downloader:
    image: alguolo/mangaworld_downloader:stable
    container_name: mangaworld_downloader
    ports:
      - "6060:6060"
    volumes:
      - ${MANGA_PATH}:/app/Downloads
    restart: unless-stopped
```
In the same directory create a ```.env``` file to set your local download paths:
```
nano .env
```
- example ```.env``` file:
```
MANGA_PATH=/path/to/your/manga/folder 
```

Start your docker compose:
```
docker compose up -d
```
The image is built for multiple architectures — Docker will automatically pull the correct version for your system (amd64 or arm64).
# Access the App

Once the container is running, you can access the interface at:
```
http://your_ip:6060
```

# How to use it
Enter URL: Paste the MangaWorld manga URL.

Select Mode: Choose whether to download individual chapters or full volumes.

Set Range (Optional): Specify a start and/or end point:
- Start & End (e.g., Start 10, End 20): Downloads items from 10 to 20 inclusive.
- Start only (e.g., Start 10): Downloads everything from item 10 up to the latest available.
- End only (e.g., End 10): Downloads everything from the first available item up to 10.
- Leave both blank: Downloads all available chapters or volumes.

# Monitoring Progress

If you want to check the raw download data, the application exposes the progress file directly via HTTP. This is useful for debugging or verifying the real-time status:
```
http://your_ip:6060/progress.json
```

# Glance Dashboard Integration

I have also created a custom Glance widget to monitor the overall download status and individual episode progress directly from your dashboard.

<img width="327" height="159" alt="Screenshot 2026-07-30 alle 13 12 23" src="https://github.com/user-attachments/assets/11d64489-11a8-4c88-9b00-f2d69142d832" />

<br>


Add your app's IP to your Glance ```.env``` file:
```
MANGA_DOWNLOADER_IP=your_container_ip:port
```
Include the widget in your Glance configuration file (e.g., ```glance.yml```):
```
widgets:
  - $include: manga_downloader.yml
```
Create a new file named ```manga_downloader.yml``` in your Glance configuration folder and paste the following:
```
- type: custom-api
  title: Manga Downloader
  cache: 2s
  subrequests:
    progress:
      url: http://${MANGA_DOWNLOADER_IP}/progress.json
  template: |
    {{ $progress := .Subrequest "progress" }}
    {{ if eq $progress.Response.StatusCode 200 }}
      {{ $mangaName   := $progress.JSON.String "manga_name" }}
      {{ $overallPct  := $progress.JSON.Float "overall.percentage" }}
      {{ $completed   := $progress.JSON.Int "overall.completed" }}
      {{ $total       := $progress.JSON.Int "overall.total" }}
      {{ $chapters    := $progress.JSON.Array "chapters" }}
      <div class="list" style="--list-gap: 12px;">
        <!-- Manga name + overall percentage -->
        <div>
          <div class="color-highlight size-h4 text-truncate">{{ $mangaName }}</div>
          <div class="flex items-center" style="gap: 10px; margin-top: 6px;">
            <div style="flex-grow: 1; background: rgba(128,128,128,0.2); border-radius: 5px; height: 6px; overflow: hidden;">
              <div style="width: {{ printf "%.1f" $overallPct }}%; background-color: var(--color-positive); height: 100%; border-radius: 5px;"></div>
            </div>
            <div class="size-sm color-highlight" style="flex-shrink: 0; min-width: 60px; text-align: right;">
              {{ printf "%.1f" $overallPct }}% ({{ $completed }}/{{ $total }})
            </div>
          </div>
        </div>
        <!-- Per-chapter list (only chapters not yet done) -->
        {{ $pending := 0 }}
        {{ range $ch := $chapters }}
          {{ if not ($ch.Bool "done") }}
            {{ $pending = add $pending 1 }}
          {{ end }}
        {{ end }}
        {{ if gt $pending 0 }}
          <ul class="list collapsible-container" data-collapse-after="0" style="--list-gap: 10px;">
            {{ range $ch := $chapters }}
              {{ if not ($ch.Bool "done") }}
                {{ $chPct := $ch.Float "percentage" }}
                <li class="flex items-center" style="gap: 10px;">
                  <div class="size-sm color-subdue" style="flex-shrink: 0; min-width: 90px;">
                    {{ $ch.String "label" }}
                  </div>
                  <div style="flex-grow: 1; background: rgba(128,128,128,0.2); border-radius: 5px; height: 4px; overflow: hidden;">
                    <div style="width: {{ printf "%.1f" $chPct }}%; background-color: var(--color-positive); height: 100%; border-radius: 5px;"></div>
                  </div>
                  <div class="size-sm color-paragraph" style="flex-shrink: 0; min-width: 42px; text-align: right;">
                    {{ printf "%.1f" $chPct }}%
                  </div>
                </li>
              {{ end }}
            {{ end }}
          </ul>
        {{ else }}
          <div class="color-positive size-sm">All chapters downloaded ✓</div>
        {{ end }}
      </div>
    {{ else }}
      <div class="color-negative size-sm text-center">
        Could not reach progress.json — is the server running?
      </div>
    {{ end }}
```
