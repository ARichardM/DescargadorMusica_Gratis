package cl.arichard.descargador;

import android.content.Intent;
import android.graphics.Typeface;
import android.os.Bundle;
import android.provider.Settings;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;
import com.google.android.material.dialog.MaterialAlertDialogBuilder;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseUser;
import org.json.JSONObject;
import java.text.DateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.Iterator;
import java.util.List;

/** Account settings hub. New settings can be added here without crowding the main screen. */
public final class SettingsActivity extends AppCompatActivity {
    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(R.layout.activity_settings);
        findViewById(R.id.btnSettingsBack).setOnClickListener(v -> finish());

        FirebaseUser user = FirebaseAuth.getInstance().getCurrentUser();
        ((TextView) findViewById(R.id.txtSettingsName)).setText(user != null && user.getDisplayName() != null
                ? user.getDisplayName() : "Cuenta de Google");
        ((TextView) findViewById(R.id.txtSettingsEmail)).setText(user != null && user.getEmail() != null ? user.getEmail() : "");
        renderDevices();

        findViewById(R.id.btnSettingsLogout).setOnClickListener(v -> new MaterialAlertDialogBuilder(this)
                .setTitle("Cerrar sesión")
                .setMessage("Tus descargas permanecerán en este dispositivo.")
                .setNegativeButton("Cancelar", null)
                .setPositiveButton("Cerrar sesión", (dialog, which) -> {
                    FirebaseAuth.getInstance().signOut();
                    startActivity(new Intent(this, LoginActivity.class)
                            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK));
                    finish();
                }).show());
    }

    private void renderDevices() {
        LinearLayout container = findViewById(R.id.layoutConnectedDevices);
        String raw = getSharedPreferences("musicbox_cloud", MODE_PRIVATE).getString("devices_json", "{}");
        String currentId = Settings.Secure.getString(getContentResolver(), Settings.Secure.ANDROID_ID);
        List<JSONObject> devices = new ArrayList<>();
        List<String> ids = new ArrayList<>();
        try {
            JSONObject root = new JSONObject(raw);
            Iterator<String> keys = root.keys();
            while (keys.hasNext()) { String key = keys.next(); ids.add(key); devices.add(root.optJSONObject(key)); }
        } catch (Exception ignored) {}
        if (devices.isEmpty()) {
            JSONObject current = new JSONObject();
            try { current.put("name", android.os.Build.MANUFACTURER + " " + android.os.Build.MODEL); current.put("platform", "Android"); current.put("lastSeen", System.currentTimeMillis()); } catch (Exception ignored) {}
            devices.add(current); ids.add(currentId);
        }
        for (int i = 0; i < devices.size(); i++) addDeviceRow(container, ids.get(i), devices.get(i), currentId);
    }

    private void addDeviceRow(LinearLayout container, String id, JSONObject device, String currentId) {
        if (device == null) return;
        LinearLayout row = new LinearLayout(this); row.setOrientation(LinearLayout.VERTICAL);
        row.setPadding(dp(16), dp(13), dp(16), dp(13)); row.setBackgroundResource(R.drawable.bg_card);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        params.bottomMargin = dp(8); row.setLayoutParams(params);
        TextView name = new TextView(this); name.setTextColor(ContextCompat.getColor(this, R.color.text_primary));
        name.setTextSize(15); name.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        name.setText(device.optString("name", "Dispositivo") + (id != null && id.equals(currentId) ? " · Este dispositivo" : ""));
        TextView detail = new TextView(this); detail.setTextColor(ContextCompat.getColor(this, R.color.text_secondary)); detail.setTextSize(12);
        long seen = device.optLong("lastSeen", 0); String date = seen > 0 ? DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(new Date(seen)) : "Sin actividad reciente";
        detail.setText(device.optString("platform", "") + " · " + date); detail.setPadding(0, dp(3), 0, 0);
        row.addView(name); row.addView(detail); container.addView(row);
    }
}
