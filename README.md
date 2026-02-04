# app.py - Aplikasi Layout Kapal Ro-Ro dengan Streamlit
import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import random
import math
from io import BytesIO
import base64

# Konfigurasi halaman
st.set_page_config(
    page_title="Ro-Ro Layout Planner",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS kustom
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1a2980;
        padding: 1rem 0;
        background: linear-gradient(90deg, #1a2980, #26d0ce);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    .vehicle-card {
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid #ddd;
        background-color: #f8f9fa;
        transition: transform 0.2s;
    }
    
    .vehicle-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        border-color: #26d0ce;
    }
    
    .stats-card {
        background-color: #f0f9ff;
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid #b3e0ff;
        margin-bottom: 1rem;
    }
    
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #1a2980, #26d0ce);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(38, 208, 206, 0.4);
    }
    
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .ship-grid {
        background-color: #e6f7ff;
        border: 2px solid #1a2980;
        border-radius: 10px;
        padding: 1rem;
    }
    
    .vehicle-color-box {
        width: 20px;
        height: 20px;
        border-radius: 4px;
        display: inline-block;
        margin-right: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Inisialisasi state session
if 'ship_layout' not in st.session_state:
    st.session_state.ship_layout = {
        'length': 50,
        'width': 15,
        'lanes': 3
    }

if 'vehicles' not in st.session_state:
    st.session_state.vehicles = []

if 'next_vehicle_id' not in st.session_state:
    st.session_state.next_vehicle_id = 1

if 'selected_vehicle' not in st.session_state:
    st.session_state.selected_vehicle = None

# Warna untuk kendaraan
vehicle_colors = [
    '#FF6B6B', '#4ECDC4', '#FFD166', '#06D6A0', 
    '#118AB2', '#EF476F', '#FFD166', '#073B4C',
    '#7209B7', '#F72585', '#3A86FF', '#FB5607'
]

# Fungsi untuk menghasilkan warna acak
def get_random_color():
    return random.choice(vehicle_colors)

# Fungsi untuk menggelapkan warna
def darken_color(color, percent):
    color = color.lstrip('#')
    rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
    rgb = tuple(max(0, min(255, int(c * (100 - percent) / 100))) for c in rgb)
    return '#%02x%02x%02x' % rgb

# Fungsi untuk memeriksa tabrakan kendaraan
def check_collision(vehicle1, vehicle2):
    x1, y1 = vehicle1['x'], vehicle1['y']
    w1, h1 = vehicle1['width_cells'], vehicle1['length_cells']
    
    x2, y2 = vehicle2['x'], vehicle2['y']
    w2, h2 = vehicle2['width_cells'], vehicle2['length_cells']
    
    return not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1)

# Fungsi untuk memeriksa apakah kendaraan cocok di kapal
def fits_on_ship(vehicle, ship_layout):
    max_x = ship_layout['lanes'] - vehicle['width_cells']
    max_y = 10 - vehicle['length_cells']
    
    if vehicle['x'] < 0 or vehicle['x'] > max_x:
        return False
    if vehicle['y'] < 0 or vehicle['y'] > max_y:
        return False
    
    return True

# Fungsi untuk menemukan posisi kosong untuk kendaraan
def find_empty_position(vehicle, ship_layout, existing_vehicles):
    max_x = ship_layout['lanes'] - vehicle['width_cells']
    max_y = 10 - vehicle['length_cells']
    
    for y in range(max_y + 1):
        for x in range(max_x + 1):
            vehicle['x'] = x
            vehicle['y'] = y
            
            collision = False
            for existing in existing_vehicles:
                if check_collision(vehicle, existing):
                    collision = True
                    break
            
            if not collision and fits_on_ship(vehicle, ship_layout):
                return True
    
    return False

# Fungsi untuk menambahkan kendaraan
def add_vehicle(name, length, width, vehicle_type="custom"):
    ship_layout = st.session_state.ship_layout
    
    # Konversi ukuran ke jumlah sel grid
    width_cells = max(1, math.ceil(width / (ship_layout['width'] / ship_layout['lanes'])))
    length_cells = max(1, math.ceil(length / (ship_layout['length'] / 10)))
    
    new_vehicle = {
        'id': st.session_state.next_vehicle_id,
        'name': name,
        'type': vehicle_type,
        'length': length,
        'width': width,
        'length_cells': length_cells,
        'width_cells': width_cells,
        'x': 0,
        'y': 0,
        'color': get_random_color()
    }
    
    # Temukan posisi kosong
    if not find_empty_position(new_vehicle, ship_layout, st.session_state.vehicles):
        st.warning(f"Tidak ada ruang yang cukup untuk {name} di kapal. Coba ukuran yang lebih kecil atau atur ulang kendaraan.")
        return
    
    st.session_state.vehicles.append(new_vehicle)
    st.session_state.next_vehicle_id += 1
    st.success(f"{name} berhasil ditambahkan ke kapal!")

# Fungsi untuk menghapus kendaraan
def remove_vehicle(vehicle_id):
    st.session_state.vehicles = [v for v in st.session_state.vehicles if v['id'] != vehicle_id]
    if st.session_state.selected_vehicle and st.session_state.selected_vehicle['id'] == vehicle_id:
        st.session_state.selected_vehicle = None

# Fungsi untuk menghitung statistik
def calculate_statistics():
    ship_layout = st.session_state.ship_layout
    
    # Luas kapal
    ship_area = ship_layout['length'] * ship_layout['width']
    
    # Luas yang ditempati kendaraan
    used_area = sum(v['length'] * v['width'] for v in st.session_state.vehicles)
    
    # Persentase penggunaan
    usage_percentage = (used_area / ship_area) * 100 if ship_area > 0 else 0
    
    # Hitung efisiensi packing
    grid_cells = ship_layout['lanes'] * 10
    used_cells = 0
    
    for vehicle in st.session_state.vehicles:
        used_cells += vehicle['length_cells'] * vehicle['width_cells']
    
    packing_efficiency = (used_cells / grid_cells) * 100 if grid_cells > 0 else 0
    
    return {
        'ship_area': ship_area,
        'used_area': used_area,
        'usage_percentage': usage_percentage,
        'packing_efficiency': packing_efficiency,
        'vehicle_count': len(st.session_state.vehicles),
        'grid_cells': grid_cells,
        'used_cells': used_cells
    }

# Fungsi untuk membuat visualisasi kapal
def create_ship_visualization():
    ship_layout = st.session_state.ship_layout
    vehicles = st.session_state.vehicles
    
    # Buat grid
    fig = go.Figure()
    
    # Tambahkan grid background
    for i in range(ship_layout['lanes'] + 1):
        fig.add_shape(
            type="line",
            x0=i, y0=0, x1=i, y1=10,
            line=dict(color="rgba(0,0,0,0.2)", width=1)
        )
    
    for j in range(11):
        fig.add_shape(
            type="line",
            x0=0, y0=j, x1=ship_layout['lanes'], y1=j,
            line=dict(color="rgba(0,0,0,0.2)", width=1)
        )
    
    # Tambahkan kendaraan
    for vehicle in vehicles:
        fig.add_shape(
            type="rect",
            x0=vehicle['x'], y0=vehicle['y'],
            x1=vehicle['x'] + vehicle['width_cells'], 
            y1=vehicle['y'] + vehicle['length_cells'],
            fillcolor=vehicle['color'],
            line=dict(color=darken_color(vehicle['color'], 30), width=2),
            opacity=0.8
        )
        
        # Tambahkan label kendaraan
        fig.add_annotation(
            x=vehicle['x'] + vehicle['width_cells'] / 2,
            y=vehicle['y'] + vehicle['length_cells'] / 2,
            text=vehicle['name'],
            showarrow=False,
            font=dict(size=10, color="white"),
            textangle=0
        )
    
    # Konfigurasi layout
    fig.update_layout(
        title="Layout Kapal Ro-Ro",
        xaxis_title="Lajur",
        yaxis_title="Posisi (depan ke belakang)",
        width=800,
        height=500,
        xaxis=dict(
            range=[0, ship_layout['lanes']],
            dtick=1,
            gridcolor="rgba(0,0,0,0.1)"
        ),
        yaxis=dict(
            range=[0, 10],
            dtick=1,
            gridcolor="rgba(0,0,0,0.1)"
        ),
        plot_bgcolor="#e6f7ff",
        paper_bgcolor="white",
        showlegend=False
    )
    
    return fig

# Fungsi untuk ekspor layout ke JSON
def export_layout():
    export_data = {
        'ship_layout': st.session_state.ship_layout,
        'vehicles': st.session_state.vehicles,
        'next_vehicle_id': st.session_state.next_vehicle_id
    }
    return json.dumps(export_data, indent=2)

# Fungsi untuk impor layout dari JSON
def import_layout(json_str):
    try:
        import_data = json.loads(json_str)
        st.session_state.ship_layout = import_data.get('ship_layout', st.session_state.ship_layout)
        st.session_state.vehicles = import_data.get('vehicles', [])
        st.session_state.next_vehicle_id = import_data.get('next_vehicle_id', st.session_state.next_vehicle_id + 1)
        return True
    except:
        return False

# UI Header
st.markdown('<h1 class="main-header">🚢 Ro-Ro Layout Planner</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Atur layout kapal Ro-Ro dengan kendaraan berukuran bervariasi</p>', unsafe_allow_html=True)

# Layout utama
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.markdown("### ⚙️ Kontrol Layout Kapal")
    
    # Input ukuran kapal
    ship_length = st.number_input(
        "Panjang Kapal (meter):", 
        min_value=10, max_value=200, value=st.session_state.ship_layout['length'], key="ship_length_input"
    )
    
    ship_width = st.number_input(
        "Lebar Kapal (meter):", 
        min_value=5, max_value=50, value=st.session_state.ship_layout['width'], key="ship_width_input"
    )
    
    lane_count = st.number_input(
        "Jumlah Lajur:", 
        min_value=1, max_value=10, value=st.session_state.ship_layout['lanes'], key="lane_count_input"
    )
    
    if st.button("🔄 Update Layout Kapal", use_container_width=True):
        st.session_state.ship_layout = {
            'length': ship_length,
            'width': ship_width,
            'lanes': lane_count
        }
        st.success("Layout kapal berhasil diupdate!")
        st.rerun()
    
    st.divider()
    
    st.markdown("### 🚗 Kendaraan Tersedia")
    st.markdown("Pilih kendaraan untuk ditambahkan:")
    
    # Kendaraan default
    if st.button("🚗 Mobil Kecil (4.5m × 1.8m)", use_container_width=True):
        add_vehicle("Mobil Kecil", 4.5, 1.8, "car")
        st.rerun()
    
    if st.button("🚙 Mobil Sedang (5m × 2m)", use_container_width=True):
        add_vehicle("Mobil Sedang", 5, 2, "car")
        st.rerun()
    
    if st.button("🚚 Truk (10m × 2.5m)", use_container_width=True):
        add_vehicle("Truk", 10, 2.5, "truck")
        st.rerun()
    
    if st.button("🚌 Bus (12m × 2.5m)", use_container_width=True):
        add_vehicle("Bus", 12, 2.5, "bus")
        st.rerun()
    
    st.divider()
    
    st.markdown("### 🛠️ Kendaraan Kustom")
    
    custom_name = st.text_input("Nama Kendaraan:", value="Kendaraan Kustom")
    custom_length = st.number_input("Panjang (m):", min_value=1.0, max_value=30.0, value=6.0, step=0.1)
    custom_width = st.number_input("Lebar (m):", min_value=1.0, max_value=10.0, value=2.0, step=0.1)
    
    if st.button("➕ Tambah Kendaraan Kustom", use_container_width=True):
        add_vehicle(custom_name, custom_length, custom_width)
        st.rerun()

with col2:
    st.markdown("### 🗺️ Layout Kapal Ro-Ro")
    
    # Visualisasi kapal
    fig = create_ship_visualization()
    st.plotly_chart(fig, use_container_width=True)
    
    # Statistik kapal
    stats = calculate_statistics()
    
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    with col_stat1:
        st.metric("Jumlah Kendaraan", stats['vehicle_count'])
    
    with col_stat2:
        st.metric("Luas Terpakai", f"{stats['used_area']:.1f} m²")
    
    with col_stat3:
        st.metric("Penggunaan Kapal", f"{stats['usage_percentage']:.1f}%")
    
    with col_stat4:
        st.metric("Efisiensi Packing", f"{stats['packing_efficiency']:.1f}%")
    
    # Kontrol kendaraan
    st.markdown("### 🎮 Kontrol Kendaraan")
    
    if st.session_state.vehicles:
        # Pilih kendaraan untuk dikontrol
        vehicle_options = {f"{v['name']} (ID: {v['id']})": v['id'] for v in st.session_state.vehicles}
        selected_vehicle_name = st.selectbox(
            "Pilih Kendaraan:",
            options=list(vehicle_options.keys()),
            index=0
        )
        
        selected_vehicle_id = vehicle_options[selected_vehicle_name]
        selected_vehicle = next(v for v in st.session_state.vehicles if v['id'] == selected_vehicle_id)
        st.session_state.selected_vehicle = selected_vehicle
        
        col_move1, col_move2, col_move3 = st.columns(3)
        
        with col_move1:
            if st.button("⬆️ Geser ke Atas", use_container_width=True):
                # Cek apakah bisa bergerak ke atas
                if selected_vehicle['y'] > 0:
                    selected_vehicle['y'] -= 1
                    # Periksa tabrakan
                    collision = False
                    for vehicle in st.session_state.vehicles:
                        if vehicle['id'] != selected_vehicle['id'] and check_collision(selected_vehicle, vehicle):
                            collision = True
                            break
                    
                    if collision or not fits_on_ship(selected_vehicle, st.session_state.ship_layout):
                        selected_vehicle['y'] += 1
                        st.warning("Tidak bisa bergerak ke atas, terjadi tabrakan atau keluar batas!")
                    st.rerun()
        
        with col_move2:
            if st.button("⬅️ Geser ke Kiri", use_container_width=True):
                if selected_vehicle['x'] > 0:
                    selected_vehicle['x'] -= 1
                    collision = False
                    for vehicle in st.session_state.vehicles:
                        if vehicle['id'] != selected_vehicle['id'] and check_collision(selected_vehicle, vehicle):
                            collision = True
                            break
                    
                    if collision or not fits_on_ship(selected_vehicle, st.session_state.ship_layout):
                        selected_vehicle['x'] += 1
                        st.warning("Tidak bisa bergerak ke kiri, terjadi tabrakan atau keluar batas!")
                    st.rerun()
            
            if st.button("➡️ Geser ke Kanan", use_container_width=True):
                max_x = st.session_state.ship_layout['lanes'] - selected_vehicle['width_cells']
                if selected_vehicle['x'] < max_x:
                    selected_vehicle['x'] += 1
                    collision = False
                    for vehicle in st.session_state.vehicles:
                        if vehicle['id'] != selected_vehicle['id'] and check_collision(selected_vehicle, vehicle):
                            collision = True
                            break
                    
                    if collision or not fits_on_ship(selected_vehicle, st.session_state.ship_layout):
                        selected_vehicle['x'] -= 1
                        st.warning("Tidak bisa bergerak ke kanan, terjadi tabrakan atau keluar batas!")
                    st.rerun()
        
        with col_move3:
            if st.button("⬇️ Geser ke Bawah", use_container_width=True):
                max_y = 10 - selected_vehicle['length_cells']
                if selected_vehicle['y'] < max_y:
                    selected_vehicle['y'] += 1
                    collision = False
                    for vehicle in st.session_state.vehicles:
                        if vehicle['id'] != selected_vehicle['id'] and check_collision(selected_vehicle, vehicle):
                            collision = True
                            break
                    
                    if collision or not fits_on_ship(selected_vehicle, st.session_state.ship_layout):
                        selected_vehicle['y'] -= 1
                        st.warning("Tidak bisa bergerak ke bawah, terjadi tabrakan atau keluar batas!")
                    st.rerun()
        
        # Tombol hapus
        if st.button("🗑️ Hapus Kendaraan Terpilih", type="secondary", use_container_width=True):
            remove_vehicle(selected_vehicle_id)
            st.success("Kendaraan berhasil dihapus!")
            st.rerun()
    
    else:
        st.info("Belum ada kendaraan di kapal. Tambahkan kendaraan dari panel kiri.")

with col3:
    st.markdown("### 📊 Detail Kendaraan")
    
    if st.session_state.selected_vehicle:
        vehicle = st.session_state.selected_vehicle
        
        st.markdown(f"""
        <div style="background-color: {vehicle['color']}20; padding: 1rem; border-radius: 10px; border-left: 5px solid {vehicle['color']};">
            <h4 style="margin-top: 0; color: #1a2980;">{vehicle['name']}</h4>
            <p><strong>Tipe:</strong> {vehicle['type'].capitalize()}</p>
            <p><strong>Ukuran:</strong> {vehicle['length']}m × {vehicle['width']}m</p>
            <p><strong>Posisi:</strong> Lajur {vehicle['x'] + 1}, Posisi {vehicle['y'] + 1}</p>
            <p><strong>Luas:</strong> {vehicle['length'] * vehicle['width']:.1f} m²</p>
            <p><strong>ID:</strong> {vehicle['id']}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Pilih kendaraan untuk melihat detail")
    
    st.divider()
    
    st.markdown("### 💾 Impor/Ekspor Layout")
    
    # Ekspor layout
    export_data = export_layout()
    st.download_button(
        label="📥 Ekspor Layout ke JSON",
        data=export_data,
        file_name="ro_ro_layout.json",
        mime="application/json",
        use_container_width=True
    )
    
    # Impor layout
    st.markdown("**Impor Layout dari JSON:**")
    uploaded_file = st.file_uploader("Pilih file JSON", type="json", label_visibility="collapsed")
    
    if uploaded_file is not None:
        json_str = uploaded_file.getvalue().decode("utf-8")
        if import_layout(json_str):
            st.success("Layout berhasil diimpor!")
            st.rerun()
        else:
            st.error("Gagal mengimpor layout. Pastikan file JSON valid.")
    
    st.divider()
    
    st.markdown("### 🛠️ Alat Tambahan")
    
    if st.button("🔄 Atur Ulang Semua Kendaraan", use_container_width=True):
        # Temukan posisi baru untuk semua kendaraan
        vehicles_copy = st.session_state.vehicles.copy()
        st.session_state.vehicles = []
        
        success_count = 0
        for vehicle in vehicles_copy:
            vehicle['x'] = 0
            vehicle['y'] = 0
            if find_empty_position(vehicle, st.session_state.ship_layout, st.session_state.vehicles):
                st.session_state.vehicles.append(vehicle)
                success_count += 1
            else:
                st.warning(f"Tidak ada ruang untuk {vehicle['name']}")
        
        if success_count == len(vehicles_copy):
            st.success("Semua kendaraan berhasil diatur ulang!")
        else:
            st.warning(f"Hanya {success_count} dari {len(vehicles_copy)} kendaraan yang berhasil ditempatkan.")
        st.rerun()
    
    if st.button("🗑️ Hapus Semua Kendaraan", type="secondary", use_container_width=True):
        st.session_state.vehicles = []
        st.session_state.selected_vehicle = None
        st.success("Semua kendaraan berhasil dihapus!")
        st.rerun()

# Footer dengan instruksi
st.divider()
st.markdown("### 📖 Cara Menggunakan:")
st.markdown("""
1. **Atur ukuran kapal** di panel kiri (panjang, lebar, jumlah lajur)
2. **Tambahkan kendaraan** dengan menekan tombol kendaraan yang tersedia atau buat kendaraan kustom
3. **Atur posisi kendaraan** dengan memilih kendaraan dan menggunakan tombol panah di panel tengah
4. **Pantau statistik** penggunaan ruang di kapal
5. **Ekspor/Impor layout** untuk menyimpan atau memuat konfigurasi
6. **Atur ulang atau hapus** kendaraan sesuai kebutuhan

**Tips:**
- Setiap kendaraan ditampilkan dengan warna berbeda untuk memudahkan identifikasi
- Sistem akan mencegah penempatan kendaraan yang bertabrakan
- Kapal dibagi menjadi grid 10×N (N = jumlah lajur)
""")

# Menampilkan data kendaraan dalam tabel
if st.session_state.vehicles:
    st.divider()
    st.markdown("### 📋 Daftar Kendaraan di Kapal")
    
    # Buat dataframe untuk tabel
    vehicles_data = []
    for vehicle in st.session_state.vehicles:
        vehicles_data.append({
            'ID': vehicle['id'],
            'Nama': vehicle['name'],
            'Tipe': vehicle['type'].capitalize(),
            'Panjang (m)': vehicle['length'],
            'Lebar (m)': vehicle['width'],
            'Luas (m²)': round(vehicle['length'] * vehicle['width'], 1),
            'Posisi X': vehicle['x'],
            'Posisi Y': vehicle['y'],
            'Warna': vehicle['color']
        })
    
    df = pd.DataFrame(vehicles_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
