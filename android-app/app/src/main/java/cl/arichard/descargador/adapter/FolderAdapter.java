package cl.arichard.descargador.adapter;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import cl.arichard.descargador.R;
import cl.arichard.descargador.model.Song;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class FolderAdapter extends RecyclerView.Adapter<FolderAdapter.FolderViewHolder> {

    public interface OnFolderClickListener {
        void onFolderClick(String folderName, List<Song> songs);
    }

    private final Context context;
    private final Map<String, List<Song>> allFolders = new LinkedHashMap<>();
    private final List<String> displayedFolderNames = new ArrayList<>();
    private final OnFolderClickListener listener;

    public FolderAdapter(Context context, Map<String, List<Song>> foldersMap, OnFolderClickListener listener) {
        this.context = context;
        this.listener = listener;
        updateFolders(foldersMap);
    }

    public void updateFolders(Map<String, List<Song>> foldersMap) {
        allFolders.clear();
        if (foldersMap != null) {
            allFolders.putAll(foldersMap);
        }
        filter("");
    }

    public void filter(String query) {
        displayedFolderNames.clear();
        String q = query != null ? query.trim().toLowerCase() : "";
        for (String name : allFolders.keySet()) {
            if (q.isEmpty() || name.toLowerCase().contains(q)) {
                displayedFolderNames.add(name);
            }
        }
        notifyDataSetChanged();
    }

    public int getDisplayedCount() { return displayedFolderNames.size(); }

    @NonNull @Override
    public FolderViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(context).inflate(R.layout.item_folder, parent, false);
        return new FolderViewHolder(v);
    }

    @Override
    public void onBindViewHolder(@NonNull FolderViewHolder holder, int position) {
        String name = displayedFolderNames.get(position);
        List<Song> songs = allFolders.get(name);
        int count = songs != null ? songs.size() : 0;

        holder.collage.setSongs(songs);
        holder.txtName.setText(name);
        holder.txtCount.setText(count + (count == 1 ? " canción" : " canciones"));

        holder.itemView.setOnClickListener(v -> {
            if (listener != null) listener.onFolderClick(name, songs);
        });
        cl.arichard.descargador.util.SafeTap.installRowTap(holder.itemView);
    }

    @Override public int getItemCount() { return displayedFolderNames.size(); }

    static class FolderViewHolder extends RecyclerView.ViewHolder {
        TextView txtName, txtCount;
        cl.arichard.descargador.util.CoverCollageView collage;

        public FolderViewHolder(@NonNull View itemView) {
            super(itemView);
            collage = itemView.findViewById(R.id.folderCollage);
            txtName = itemView.findViewById(R.id.txtFolderName);
            txtCount = itemView.findViewById(R.id.txtFolderSongCount);
        }
    }
}
