package cl.arichard.descargador.model;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;

public class Playlist implements Serializable {
    private String name;
    private List<String> songPaths;

    public Playlist(String name) {
        this.name = name;
        this.songPaths = new ArrayList<>();
    }

    public Playlist(String name, List<String> songPaths) {
        this.name = name;
        this.songPaths = songPaths != null ? songPaths : new ArrayList<>();
    }

    public String getName() { return name; }
    public List<String> getSongPaths() { return songPaths; }
    public int getSongCount() { return songPaths.size(); }
    public boolean isFavorites() { return "Favoritos".equalsIgnoreCase(name); }
}
