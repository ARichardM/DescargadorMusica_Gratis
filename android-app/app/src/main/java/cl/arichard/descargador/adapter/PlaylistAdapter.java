package cl.arichard.descargador.adapter;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.TextView;
import androidx.appcompat.widget.SwitchCompat;
import cl.arichard.descargador.data.PlaylistManager;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import cl.arichard.descargador.R;
import java.util.ArrayList;
import java.util.List;

public class PlaylistAdapter extends RecyclerView.Adapter<PlaylistAdapter.PlaylistViewHolder> {

    public interface OnPlaylistClickListener {
        void onPlaylistClick(String playlistName);
        void onDeleteClick(String playlistName);
        void onAutoDownloadChanged(String playlistName, boolean enabled);
    }

    private final List<cl.arichard.descargador.model.Song> library = new ArrayList<>();
    public void setLibrary(List<cl.arichard.descargador.model.Song> songs) {
        library.clear(); library.addAll(songs); notifyDataSetChanged();
    }
    private final Context context;
    private final List<String> originalNames = new ArrayList<>();
    private final List<String> displayedNames = new ArrayList<>();
    private final OnPlaylistClickListener listener;

    public PlaylistAdapter(Context context, List<String> playlistNames, OnPlaylistClickListener listener) {
        this.context = context;
        this.listener = listener;
        updatePlaylists(playlistNames);
    }

    public void updatePlaylists(List<String> names) {
        originalNames.clear();
        if (names != null) {
            originalNames.addAll(names);
        }
        filter("");
    }

    public void filter(String query) {
        displayedNames.clear();
        String q = query != null ? query.trim().toLowerCase() : "";
        for (String name : originalNames) {
            if (q.isEmpty() || name.toLowerCase().contains(q)) {
                displayedNames.add(name);
            }
        }
        notifyDataSetChanged();
    }

    public int getDisplayedCount() { return displayedNames.size(); }

    @NonNull @Override
    public PlaylistViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(context).inflate(R.layout.item_playlist, parent, false);
        return new PlaylistViewHolder(v);
    }

    @Override
    public void onBindViewHolder(@NonNull PlaylistViewHolder holder, int position) {
        String name = displayedNames.get(position);
        holder.txtName.setText(name);

        boolean isFav = "Favoritos".equals(name);
        holder.btnDelete.setVisibility(isFav ? View.GONE : View.VISIBLE);
        List<cl.arichard.descargador.model.Song> songs = PlaylistManager.getInstance(context).resolveSongs(name, library);
        holder.collage.setSongs(songs);
        holder.txtCount.setText(songs.size() + (songs.size() == 1 ? " canción" : " canciones"));
        holder.autoDownload.setOnCheckedChangeListener(null);
        holder.autoDownload.setChecked(PlaylistManager.getInstance(context).isAutoDownloadEnabled(name));
        holder.autoDownload.setOnCheckedChangeListener((button, checked) -> {
            PlaylistManager.getInstance(context).setAutoDownloadEnabled(name, checked);
            if (listener != null) listener.onAutoDownloadChanged(name, checked);
        });

        holder.itemView.setOnClickListener(v -> {
            if (listener != null) listener.onPlaylistClick(name);
        });

        holder.btnDelete.setOnClickListener(v -> {
            if (listener != null) listener.onDeleteClick(name);
        });
        cl.arichard.descargador.util.SafeTap.install(holder.btnDelete);
        cl.arichard.descargador.util.SafeTap.install(holder.autoDownload);
        cl.arichard.descargador.util.SafeTap.installRowTap(holder.itemView);
    }

    @Override public int getItemCount() { return displayedNames.size(); }

    static class PlaylistViewHolder extends RecyclerView.ViewHolder {
        TextView txtName, txtCount;
        ImageView btnDelete;
        cl.arichard.descargador.util.CoverCollageView collage;
        SwitchCompat autoDownload;

        public PlaylistViewHolder(@NonNull View itemView) {
            super(itemView);
            txtName = itemView.findViewById(R.id.txtPlaylistName);
            collage = itemView.findViewById(R.id.playlistCollage);
            txtCount = itemView.findViewById(R.id.txtPlaylistCount);
            btnDelete = itemView.findViewById(R.id.btnDeletePlaylist);
            autoDownload = itemView.findViewById(R.id.switchAutoDownload);
        }
    }
}
