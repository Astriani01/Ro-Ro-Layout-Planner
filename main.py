# app.py - Aplikasi Layout Kapal Ro-Ro dengan Diagram Kartesius
import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
import plotly.express as px
import random
import math
from io import BytesIO
from dataclasses import dataclass
from typing import List, Tuple, Optional

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
    
    .capacity-meter {
        height: 10px;
        background-color: #e9ecef;
        border-radius: 5px;
        margin: 10px 0;
        overflow: hidden;
    }
    
    .capacity-fill {
        height: 100%;
        border-radius: 5px;
        transition: width 0.3s ease;
    }
    
    .coordinate-display {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 0.5rem;
        font-family: monospace;
        font-size: 0.9rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Data class untuk kendaraan
@dataclass
class Vehicle:
    id: int
    name: str
    type: str
    length: float  # dalam meter
    width: float   # dalam meter
    x: float       # posisi x (meter dari kiri)
    y: float       # posisi y (meter dari depan)
    color: str
    icon: str

# Inisialisasi state session
if 'ship_layout' not in st.session_state:
    st.session_state.ship_layout = {
        'length': 50,    # meter
        'width': 15      # meter
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
    '#118AB2', '#EF476F', '#7209B7', '#073B4C',
    '#F72585', '#3A86FF', '#FB5607', '#8338EC',
    '#3A86FF', '#FF006E', '#FFBE0B', '#FB5607'
]

# Ikon untuk tipe kendaraan
vehicle_icons = {
    'motor': '🏍️',
    'car': '🚗',
    'truck': '🚚',
    'bus': '🚌',
    'custom': '🚙'
}

# Fungsi untuk menghasilkan warna acak
def get_random_color():
    return random.choice(vehicle_colors)

# Fungsi untuk menggelapkan warna
def darken_color(color, percent):
    color = color.lstrip('#')
    rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
    rgb = tuple(max(0, min(255, int(c * (100 - percent) / 100))) for c in rgb)
    return '#%02x%02x%02x' % rgb

# Fungsi untuk memeriksa tabrakan kendaraan (dalam meter)
def check_collision(vehicle1, vehicle2):
    x1, y1 = vehicle1['x'], vehicle1['y']
    w1, h1 = vehicle1['width'], vehicle1['length']
    
    x2, y2 = vehicle2['x'], vehicle2['y']
    w2, h2 = vehicle2['width'], vehicle2['length']
    
    # Check if rectangles overlap
    return not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1)

# Fungsi untuk memeriksa apakah kendaraan cocok di kapal
def fits_on_ship(vehicle, ship_layout):
    # Cek apakah kendaraan berada dalam batas kapal
    if vehicle['x'] < 0 or vehicle['x'] + vehicle['width'] > ship_layout['width']:
        return False
    if vehicle['y'] < 0 or vehicle['y'] + vehicle['length'] > ship_layout['length']:
        return False
    return True

# Fungsi untuk menemukan posisi kosong untuk kendaraan
def find_empty_position(vehicle, ship_layout, existing_vehicles, grid_step=0.5):
    """
    Mencari posisi kosong untuk kendaraan dengan grid tertentu
    grid_step: resolusi pencarian dalam meter
    """
    max_x = ship_layout['width'] - vehicle['width']
    max_y = ship_layout['length'] - vehicle['length']
    
    # Generate grid points
    x_points = np.arange(0, max_x + grid_step, grid_step)
    y_points = np.arange(0, max_y + grid_step, grid_step)
    
    for y in y_points:
        for x in x_points:
            vehicle['x'] = round(x, 2)
            vehicle['y'] = round(y, 2)
            
            collision = False
            for existing in existing_vehicles:
                if check_collision(vehicle, existing):
                    collision = True
                    break
            
            if not collision and fits_on_ship(vehicle, ship_layout):
                return True
    
    return False

# Fungsi untuk menambahkan kendaraan
def add_vehicle(name, length, width, vehicle_type="custom", icon="🚙"):
    ship_layout = st.session_state.ship_layout
    
    new_vehicle = {
        'id': st.session_state.next_vehicle_id,
        'name': name,
        'type': vehicle_type,
        'length': length,
        'width': width,
        'x': 0,  # posisi awal dalam meter
        'y': 0,  # posisi awal dalam meter
        'color': get_random_color(),
        'icon': icon
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
    
    # Hitung jumlah kendaraan per tipe
    vehicle_types = {}
    for vehicle in st.session_state.vehicles:
        if vehicle['type'] not in vehicle_types:
            vehicle_types[vehicle['type']] = 0
        vehicle_types[vehicle['type']] += 1
    
    return {
        'ship_area': ship_area,
        'used_area': used_area,
        'usage_percentage': usage_percentage,
        'vehicle_count': len(st.session_state.vehicles),
        'vehicle_types': vehicle_types,
    }

# Fungsi untuk membuat diagram sederhana dengan titik grid
def create_grid_diagram():
    """Membuat diagram grid dengan titik-titik dan kendaraan"""
    ship_layout = st.session_state.ship_layout
    vehicles = st.session_state.vehicles
    
    # Buat grid titik
    grid_size = 0.5  # meter
    x = np.arange(0, ship_layout['width'] + grid_size, grid_size)
    y = np.arange(0, ship_layout['length'] + grid_size, grid_size)
    
    X, Y = np.meshgrid(x, y)
    
    # Buat figure
    fig = go.Figure()
    
    # Tambahkan titik grid
    fig.add_trace(go.Scatter(
        x=X.flatten(),
        y=Y.flatten(),
        mode='markers',
        marker=dict(
            size=4,
            color='lightgray',
            symbol='circle',
            opacity=0.5
        ),
        name='Grid Points',
        showlegend=False
    ))
    
    # Outline kapal
    ship_x = [0, ship_layout['width'], ship_layout['width'], 0, 0]
    ship_y = [0, 0, ship_layout['length'], ship_layout['length'], 0]
    
    fig.add_trace(go.Scatter(
        x=ship_x,
        y=ship_y,
        mode='lines',
        line=dict(color='blue', width=3),
        fill='toself',
        fillcolor='rgba(135, 206, 235, 0.1)',
        name='Kapal'
    ))
    
    # Tambahkan kendaraan
    for vehicle in vehicles:
        # Hitung posisi dalam grid
        x0 = vehicle['x']
        y0 = vehicle['y']
        x1 = vehicle['x'] + vehicle['width']
        y1 = vehicle['y'] + vehicle['length']
        
        # Persegi panjang kendaraan
        fig.add_trace(go.Scatter(
            x=[x0, x1, x1, x0, x0],
            y=[y0, y0, y1, y1, y0],
            mode='lines+markers',
            fill='toself',
            fillcolor=vehicle['color'],
            line=dict(color=darken_color(vehicle['color'], 30), width=2),
            marker=dict(size=0),  # Tidak menampilkan marker di sudut
            name=vehicle['name'],
            text=f"{vehicle['name']}<br>{vehicle['length']}m × {vehicle['width']}m",
            hoverinfo='text'
        ))
        
        # Tambahkan titik di tengah dengan ikon
        center_x = (x0 + x1) / 2
        center_y = (y0 + y1) / 2
        
        fig.add_trace(go.Scatter(
            x=[center_x],
            y=[center_y],
            mode='markers+text',
            marker=dict(size=0),
            text=[vehicle['icon']],
            textfont=dict(size=20),
            showlegend=False
        ))
    
    # Konfigurasi layout
    fig.update_layout(
        title="Diagram Grid Kapal (Skala Sebenarnya)",
        xaxis_title="Lebar (meter)",
        yaxis_title="Panjang (meter)",
        width=800,
        height=600,
        xaxis=dict(
            scaleanchor="y",
            scaleratio=1,
            constrain='domain'
        ),
        yaxis=dict(
            scaleanchor="x",
            scaleratio=1,
            constrain='domain'
        ),
        plot_bgcolor='white',
        showlegend=False
    )
    
    return fig

# Fungsi untuk ekspor layout ke JSON
def export_layout():
    export_data = {
        'ship_layout': st.session_state.ship_layout,
        'vehicles': st.session_state.vehicles,
        'next_vehicle_id': st.session_state.next_vehicle_id,
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
st.markdown('<p class="subtitle">Atur layout kapal Ro-Ro dengan diagram kartesius skala 1:1</p>', unsafe_allow_html=True)

# Panel informasi
st.markdown("### 📐 Informasi Skala 1:1")
with st.expander("Klik untuk melihat penjelasan skala"):
    ship_layout = st.session_state.ship_layout
    
    col_scale1, col_scale2 = st.columns(2)
    with col_scale1:
        st.metric("Ukuran Kapal", f"{ship_layout['length']}m × {ship_layout['width']}m")
    with col_scale2:
        st.metric("Luas Kapal", f"{ship_layout['length'] * ship_layout['width']:.1f} m²")
    
    st.info(f"""
    **Diagram Kartesius Skala 1:1:**
    - **Sumbu X**: Lebar kapal (0 sampai {ship_layout['width']} meter)
    - **Sumbu Y**: Panjang kapal (0 sampai {ship_layout['length']} meter)
    - **Setiap titik grid**: Berjarak 0.5 meter
    - **Ukuran kendaraan**: Ditampilkan sesuai ukuran sebenarnya
    - **Skala**: 1 pixel = 1 meter (proporsional)
    """)

# Layout utama
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.markdown("### ⚙️ Kontrol Layout Kapal")
    
    # Input ukuran kapal (tanpa jumlah lajur)
    ship_length = st.number_input(
        "Panjang Kapal (meter):", 
        min_value=10.0, max_value=1000000.0, value=float(st.session_state.ship_layout['length']), 
        step=0.5, key="ship_length_input", format="%.1f"
    )
    
    ship_width = st.number_input(
        "Lebar Kapal (meter):", 
        min_value=5.0, max_value=1000000.0, value=float(st.session_state.ship_layout['width']), 
        step=0.5, key="ship_width_input", format="%.1f"
    )
    
    # Update layout kapal (tanpa jumlah lajur)
    if st.button("🔄 Update Layout Kapal", use_container_width=True):
        st.session_state.ship_layout = {
            'length': float(ship_length),
            'width': float(ship_width)
        }
        
        # Periksa apakah kendaraan masih muat
        for vehicle in st.session_state.vehicles:
            if not fits_on_ship(vehicle, st.session_state.ship_layout):
                st.warning(f"Kendaraan {vehicle['name']} tidak muat setelah resize kapal!")
                # Cari posisi baru
                if not find_empty_position(vehicle, st.session_state.ship_layout, 
                                         [v for v in st.session_state.vehicles if v['id'] != vehicle['id']]):
                    st.error(f"Tidak ada ruang untuk {vehicle['name']}. Kendaraan akan dihapus.")
                    remove_vehicle(vehicle['id'])
        
        st.success("Layout kapal berhasil diupdate!")
        st.rerun()
    
    st.divider()
    
    st.markdown("### 🚗 Kendaraan Tersedia")
    st.markdown("Pilih kendaraan untuk ditambahkan:")
    
    # Kendaraan default dengan ukuran sebenarnya
    col_veh1, col_veh2 = st.columns(2)
    
    with col_veh1:
        if st.button(f"🏍️ Motor\n2.0m × 0.8m", 
                    use_container_width=True, 
                    help="Motor: Panjang 2.0m, Lebar 0.8m"):
            add_vehicle("Motor", 2.0, 0.8, "motor", "🏍️")
            st.rerun()
        
        if st.button(f"🚗 Mobil Sedang\n5.0m × 2.0m", 
                    use_container_width=True, 
                    help="Mobil Sedang: Panjang 5.0m, Lebar 2.0m"):
            add_vehicle("Mobil Sedang", 5.0, 2.0, "car", "🚗")
            st.rerun()
    
    with col_veh2:
        if st.button(f"🚙 Mobil Kecil\n4.5m × 1.8m", 
                    use_container_width=True, 
                    help="Mobil Kecil: Panjang 4.5m, Lebar 1.8m"):
            add_vehicle("Mobil Kecil", 4.5, 1.8, "car", "🚙")
            st.rerun()
        
        if st.button(f"🚚 Truk\n10.0m × 2.5m", 
                    use_container_width=True, 
                    help="Truk: Panjang 10.0m, Lebar 2.5m"):
            add_vehicle("Truk", 10.0, 2.5, "truck", "🚚")
            st.rerun()
    
    if st.button(f"🚌 Bus\n12.0m × 2.5m", 
                use_container_width=True, 
                help="Bus: Panjang 12.0m, Lebar 2.5m"):
        add_vehicle("Bus", 12.0, 2.5, "bus", "🚌")
        st.rerun()
    
    st.divider()
    
    st.markdown("### 🛠️ Kendaraan Kustom")
    
    custom_name = st.text_input("Nama Kendaraan:", value="Kendaraan Kustom")
    
    col_custom_size1, col_custom_size2 = st.columns(2)
    with col_custom_size1:
        custom_length = st.number_input("Panjang (m):", min_value=0.5, max_value=30.0, value=6.0, step=0.1, format="%.1f")
    with col_custom_size2:
        custom_width = st.number_input("Lebar (m):", min_value=0.5, max_value=10.0, value=2.0, step=0.1, format="%.1f")
    
    col_custom1, col_custom2 = st.columns(2)
    with col_custom1:
        custom_type = st.selectbox("Tipe Kendaraan:", ["motor", "car", "truck", "bus", "custom"])
    with col_custom2:
        custom_icon = st.selectbox("Ikon:", ["🏍️", "🚗", "🚙", "🚚", "🚌", "🚐", "🛻"])
    
    if st.button("➕ Tambah Kendaraan Kustom", use_container_width=True):
        add_vehicle(custom_name, custom_length, custom_width, custom_type, custom_icon)
        st.rerun()

with col2:
    st.markdown("### 🗺️ Layout Kapal (Diagram Grid Skala 1:1)")
    
    # Hanya tampilkan diagram grid sederhana
    fig = create_grid_diagram()
    st.plotly_chart(fig, use_container_width=True)
    
    # Statistik kapal
    stats = calculate_statistics()
    
    # Meter kapasitas kendaraan
    st.markdown(f"**Jumlah Kendaraan:** {len(st.session_state.vehicles)}")
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    
    with col_stat1:
        st.metric("Jumlah Kendaraan", stats['vehicle_count'])
    
    with col_stat2:
        st.metric("Luas Terpakai", f"{stats['used_area']:.1f} m²")
    
    with col_stat3:
        st.metric("Penggunaan Kapal", f"{stats['usage_percentage']:.1f}%")
    
    # Informasi posisi
    with st.expander("📍 Informasi Koordinat"):
        ship_layout = st.session_state.ship_layout
        st.write(f"**Sistem Koordinat:**")
        st.write(f"- Titik (0, 0): Pojok kiri depan kapal")
        st.write(f"- Titik ({ship_layout['width']}, 0): Pojok kanan depan kapal")
        st.write(f"- Titik (0, {ship_layout['length']}): Pojok kiri belakang kapal")
        st.write(f"- Titik ({ship_layout['width']}, {ship_layout['length']}): Pojok kanan belakang kapal")
        
        if st.session_state.vehicles:
            st.write("**Koordinat Kendaraan:**")
            for vehicle in st.session_state.vehicles:
                st.code(f"{vehicle['name']}: ({vehicle['x']:.1f}, {vehicle['y']:.1f}) - ({vehicle['x']+vehicle['width']:.1f}, {vehicle['y']+vehicle['length']:.1f})")
    
    # Statistik per tipe kendaraan
    if stats['vehicle_types']:
        st.markdown("### 📈 Distribusi Kendaraan")
        type_data = pd.DataFrame({
            'Tipe': list(stats['vehicle_types'].keys()),
            'Jumlah': list(stats['vehicle_types'].values())
        })
        
        # Tampilkan chart kecil
        col_chart1, col_chart2 = st.columns([2, 1])
        with col_chart1:
            st.bar_chart(type_data.set_index('Tipe'))
        with col_chart2:
            st.dataframe(type_data, use_container_width=True, hide_index=True)
    
    # Kontrol kendaraan dengan input koordinat
    st.markdown("### 🎮 Kontrol Kendaraan (Koordinat)")
    
    if st.session_state.vehicles:
        # Pilih kendaraan untuk dikontrol
        vehicle_options = {f"{v['icon']} {v['name']} (ID: {v['id']})": v['id'] for v in st.session_state.vehicles}
        selected_vehicle_name = st.selectbox(
            "Pilih Kendaraan:",
            options=list(vehicle_options.keys()),
            index=0
        )
        
        selected_vehicle_id = vehicle_options[selected_vehicle_name]
        selected_vehicle = next(v for v in st.session_state.vehicles if v['id'] == selected_vehicle_id)
        st.session_state.selected_vehicle = selected_vehicle
        
        # Input koordinat manual
        st.markdown("**Atur Posisi Manual:**")
        col_pos1, col_pos2 = st.columns(2)
        
        with col_pos1:
            new_x = st.number_input(
                "Posisi X (meter dari kiri):", 
                min_value=0.0, max_value=ship_width, 
                value=float(selected_vehicle['x']), step=0.1, format="%.1f",
                key=f"pos_x_{selected_vehicle_id}"
            )
        
        with col_pos2:
            new_y = st.number_input(
                "Posisi Y (meter dari depan):", 
                min_value=0.0, max_value=ship_length, 
                value=float(selected_vehicle['y']), step=0.1, format="%.1f",
                key=f"pos_y_{selected_vehicle_id}"
            )
        
        if st.button("📍 Pindah ke Posisi", use_container_width=True):
            # Simpan posisi lama
            old_x, old_y = selected_vehicle['x'], selected_vehicle['y']
            
            # Update posisi
            selected_vehicle['x'] = new_x
            selected_vehicle['y'] = new_y
            
            # Cek tabrakan dan batas
            collision = False
            for vehicle in st.session_state.vehicles:
                if vehicle['id'] != selected_vehicle_id and check_collision(selected_vehicle, vehicle):
                    collision = True
                    st.warning(f"Tabrakan dengan {vehicle['name']}!")
                    break
            
            if not fits_on_ship(selected_vehicle, st.session_state.ship_layout):
                st.error("Posisi di luar batas kapal!")
                selected_vehicle['x'], selected_vehicle['y'] = old_x, old_y
            elif collision:
                selected_vehicle['x'], selected_vehicle['y'] = old_x, old_y
            else:
                st.success("Posisi berhasil diubah!")
            st.rerun()
        
        # Tombol kontrol arah
        st.markdown("**Kontrol Arah:**")
        col_move1, col_move2, col_move3 = st.columns(3)
        
        move_step = st.slider("Langkah pergerakan (meter):", 0.1, 2.0, 0.5, 0.1)
        
        with col_move1:
            if st.button("⬆️ Maju", use_container_width=True):
                selected_vehicle['y'] += move_step
                if not fits_on_ship(selected_vehicle, st.session_state.ship_layout) or any(check_collision(selected_vehicle, v) for v in st.session_state.vehicles if v['id'] != selected_vehicle_id):
                    selected_vehicle['y'] -= move_step
                st.rerun()
        
        with col_move2:
            if st.button("⬅️ Kiri", use_container_width=True):
                selected_vehicle['x'] -= move_step
                if not fits_on_ship(selected_vehicle, st.session_state.ship_layout) or any(check_collision(selected_vehicle, v) for v in st.session_state.vehicles if v['id'] != selected_vehicle_id):
                    selected_vehicle['x'] += move_step
                st.rerun()
            
            if st.button("➡️ Kanan", use_container_width=True):
                selected_vehicle['x'] += move_step
                if not fits_on_ship(selected_vehicle, st.session_state.ship_layout) or any(check_collision(selected_vehicle, v) for v in st.session_state.vehicles if v['id'] != selected_vehicle_id):
                    selected_vehicle['x'] -= move_step
                st.rerun()
        
        with col_move3:
            if st.button("⬇️ Mundur", use_container_width=True):
                selected_vehicle['y'] -= move_step
                if not fits_on_ship(selected_vehicle, st.session_state.ship_layout) or any(check_collision(selected_vehicle, v) for v in st.session_state.vehicles if v['id'] != selected_vehicle_id):
                    selected_vehicle['y'] += move_step
                st.rerun()
        
        # Tombol aksi (tanpa duplikat kendaraan)
        if st.button("🗑️ Hapus Kendaraan", type="secondary", use_container_width=True):
            remove_vehicle(selected_vehicle_id)
            st.success("Kendaraan berhasil dihapus!")
            st.rerun()
    
    else:
        st.info("Belum ada kendaraan di kapal. Tambahkan kendaraan dari panel kiri.")

with col3:
    st.markdown("### 📊 Detail Kendaraan (Koordinat)")
    
    if st.session_state.selected_vehicle:
        vehicle = st.session_state.selected_vehicle
        
        st.markdown(f"""
        <div style="background-color: {vehicle['color']}20; padding: 1rem; border-radius: 10px; border-left: 5px solid {vehicle['color']};">
            <h4 style="margin-top: 0; color: #1a2980;">{vehicle['icon']} {vehicle['name']}</h4>
            <p><strong>Tipe:</strong> {vehicle['type'].capitalize()}</p>
            <p><strong>Ukuran:</strong> {vehicle['length']}m × {vehicle['width']}m</p>
            <div class="coordinate-display">
                <strong>Koordinat:</strong><br>
                • Kiri-Bawah: ({vehicle['x']:.1f}, {vehicle['y']:.1f})<br>
                • Kanan-Atas: ({vehicle['x']+vehicle['width']:.1f}, {vehicle['y']+vehicle['length']:.1f})
            </div>
            <p><strong>Luas:</strong> {vehicle['length'] * vehicle['width']:.1f} m²</p>
            <p><strong>ID:</strong> {vehicle['id']}</p>
            <div style="display: flex; align-items: center; margin-top: 10px;">
                <div class="vehicle-color-box" style="background-color: {vehicle['color']};"></div>
                <span>Warna kendaraan</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Edit kendaraan
        st.markdown("---")
        st.markdown("### ✏️ Edit Kendaraan")
        
        with st.form(key=f"edit_vehicle_{vehicle['id']}"):
            new_name = st.text_input("Nama Baru:", value=vehicle['name'])
            
            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                new_length = st.number_input("Panjang Baru (m):", 
                                           value=float(vehicle['length']), 
                                           min_value=0.5, max_value=30.0, step=0.1,
                                           format="%.1f")
            with col_edit2:
                new_width = st.number_input("Lebar Baru (m):", 
                                          value=float(vehicle['width']), 
                                          min_value=0.5, max_value=10.0, step=0.1,
                                          format="%.1f")
            
            if st.form_submit_button("💾 Simpan Perubahan", use_container_width=True):
                # Simpan ukuran lama
                old_length, old_width = vehicle['length'], vehicle['width']
                
                # Update data kendaraan
                vehicle['name'] = new_name
                vehicle['length'] = new_length
                vehicle['width'] = new_width
                
                # Check if still fits
                if not fits_on_ship(vehicle, st.session_state.ship_layout):
                    st.warning("Ukuran baru tidak muat di posisi saat ini! Mencari posisi baru...")
                    # Cari posisi baru
                    if not find_empty_position(vehicle, st.session_state.ship_layout, 
                                             [v for v in st.session_state.vehicles if v['id'] != vehicle['id']]):
                        st.error("Tidak ada ruang yang cukup untuk ukuran baru ini!")
                        # Revert changes
                        vehicle['length'], vehicle['width'] = old_length, old_width
                    else:
                        st.success("Kendaraan berhasil dipindahkan ke posisi baru!")
                else:
                    st.success("Kendaraan berhasil diperbarui!")
                st.rerun()
    else:
        st.info("Pilih kendaraan untuk melihat detail")
    
    st.divider()
    
    st.markdown("### 💾 Impor/Ekspor Layout")
    
    # Ekspor layout
    export_data = export_layout()
    st.download_button(
        label="📥 Ekspor Layout ke JSON",
        data=export_data,
        file_name=f"ro_ro_layout_{len(st.session_state.vehicles)}_kendaraan.json",
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
        # Algoritma penempatan otomatis sederhana
        vehicles_sorted = sorted(st.session_state.vehicles, 
                               key=lambda v: v['length'] * v['width'], 
                               reverse=True)
        
        st.session_state.vehicles = []
        
        for vehicle in vehicles_sorted:
            vehicle['x'] = 0
            vehicle['y'] = 0
            if find_empty_position(vehicle, st.session_state.ship_layout, st.session_state.vehicles):
                st.session_state.vehicles.append(vehicle)
            else:
                st.warning(f"Tidak ada ruang untuk {vehicle['name']}")
        
        st.success("Kendaraan berhasil diatur ulang!")
        st.rerun()
    
    if st.button("🗑️ Hapus Semua Kendaraan", type="secondary", use_container_width=True):
        st.session_state.vehicles = []
        st.session_state.selected_vehicle = None
        st.success("Semua kendaraan berhasil dihapus!")
        st.rerun()

# Footer dengan instruksi
st.divider()
st.markdown("### 📖 Cara Menggunakan (Diagram Kartesius):")
st.markdown("""
1. **Diagram Kartesius Skala 1:1**: 
   - Sumbu X = Lebar kapal (meter dari kiri)
   - Sumbu Y = Panjang kapal (meter dari depan)
   - Setiap titik = posisi yang mungkin untuk penempatan kendaraan

2. **Ukuran Sebenarnya**:
   - Kendaraan ditampilkan dengan ukuran sebenarnya (dalam meter)
   - Motor: 2.0m × 0.8m
   - Mobil Kecil: 4.5m × 1.8m
   - Mobil Sedang: 5.0m × 2.0m
   - Truk: 10.0m × 2.5m
   - Bus: 12.0m × 2.5m

3. **Kontrol Presisi**:
   - Atur posisi dengan input koordinat (X, Y) dalam meter
   - Gunakan tombol arah dengan langkah yang dapat disesuaikan
   - Sistem otomatis mencegah tabrakan

4. **Visualisasi**:
   - Titik-titik grid untuk referensi posisi
   - Garis bantu untuk lajur kapal
   - Skala proporsional 1:1 antara gambar dan ukuran sebenarnya
""")

# Menampilkan data kendaraan dalam tabel
if st.session_state.vehicles:
    st.divider()
    st.markdown("### 📋 Daftar Kendaraan di Kapal (Koordinat)")
    
    # Buat dataframe untuk tabel dengan koordinat
    vehicles_data = []
    for vehicle in st.session_state.vehicles:
        vehicles_data.append({
            'ID': vehicle['id'],
            'Ikon': vehicle['icon'],
            'Nama': vehicle['name'],
            'Tipe': vehicle['type'].capitalize(),
            'Panjang (m)': vehicle['length'],
            'Lebar (m)': vehicle['width'],
            'X (m)': f"{vehicle['x']:.1f}",
            'Y (m)': f"{vehicle['y']:.1f}",
            'Luas (m²)': f"{vehicle['length'] * vehicle['width']:.1f}",
            'Warna': vehicle['color']
        })
    
    df = pd.DataFrame(vehicles_data)
    
    # Format dataframe dengan warna
    def color_row(row):
        color = row['Warna']
        return [f'background-color: {color}20' for _ in row]
    
    styled_df = df.style.apply(color_row, axis=1)
    st.dataframe(styled_df, use_container_width=True, hide_index=True, 
                column_config={
                    "Warna": st.column_config.TextColumn(disabled=True)
                })
    
    # Ringkasan
    total_area = sum(v['length'] * v['width'] for v in st.session_state.vehicles)
    ship_area = st.session_state.ship_layout['length'] * st.session_state.ship_layout['width']
    
    st.markdown(f"""
    **Ringkasan:**
    - **Total Kendaraan:** {len(st.session_state.vehicles)}
    - **Total Luas Terpakai:** {total_area:.1f} m² dari {ship_area:.1f} m² ({total_area/ship_area*100:.1f}%)
    - **Motor:** {stats['vehicle_types'].get('motor', 0)} unit
    - **Mobil:** {stats['vehicle_types'].get('car', 0)} unit
    - **Truk:** {stats['vehicle_types'].get('truck', 0)} unit
    - **Bus:** {stats['vehicle_types'].get('bus', 0)} unit
    - **Kustom:** {stats['vehicle_types'].get('custom', 0)} unit
    """)
