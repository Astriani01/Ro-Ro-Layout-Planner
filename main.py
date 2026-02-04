# app.py - Aplikasi Layout Kapal Ro-Ro Sederhana
import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
import random
import math
from io import BytesIO

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
</style>
""", unsafe_allow_html=True)

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

if 'max_vehicles' not in st.session_state:
    st.session_state.max_vehicles = 20

# Warna untuk kendaraan
vehicle_colors = [
    '#FF6B6B', '#4ECDC4', '#FFD166', '#06D6A0', 
    '#118AB2', '#EF476F', '#7209B7', '#073B4C',
    '#F72585', '#3A86FF', '#FB5607', '#8338EC'
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
def find_empty_position(vehicle, ship_layout, existing_vehicles, grid_step=1.0):
    """
    Mencari posisi kosong untuk kendaraan
    """
    max_x = ship_layout['width'] - vehicle['width']
    max_y = ship_layout['length'] - vehicle['length']
    
    # Coba posisi yang mungkin
    for y in np.arange(0, max_y + grid_step, grid_step):
        for x in np.arange(0, max_x + grid_step, grid_step):
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
    # Cek apakah sudah mencapai batas maksimum kendaraan
    if len(st.session_state.vehicles) >= st.session_state.max_vehicles:
        st.warning(f"Tidak dapat menambahkan kendaraan. Batas maksimum {st.session_state.max_vehicles} kendaraan telah tercapai.")
        return
    
    ship_layout = st.session_state.ship_layout
    
    new_vehicle = {
        'id': st.session_state.next_vehicle_id,
        'name': name,
        'type': vehicle_type,
        'length': length,
        'width': width,
        'x': 0,
        'y': 0,
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
        'capacity_percentage': (len(st.session_state.vehicles) / st.session_state.max_vehicles) * 100
    }

# FUNGSI UTAMA: Membuat visualisasi kapal dengan titik-titik
def create_ship_dots_visualization():
    ship_layout = st.session_state.ship_layout
    vehicles = st.session_state.vehicles
    
    # Buat figure
    fig = go.Figure()
    
    # Tambahkan outline kapal (background)
    fig.add_shape(
        type="rect",
        x0=0, y0=0,
        x1=ship_layout['width'], 
        y1=ship_layout['length'],
        fillcolor='#f8f9fa',
        line=dict(color='#1a2980', width=3),
        layer='below'
    )
    
    # Tambahkan grid lines
    grid_size = 5  # meter
    for x in np.arange(0, ship_layout['width'] + grid_size, grid_size):
        fig.add_shape(
            type="line",
            x0=x, y0=0, x1=x, y1=ship_layout['length'],
            line=dict(color="rgba(0,0,0,0.1)", width=1, dash="dash"),
            layer='below'
        )
    
    for y in np.arange(0, ship_layout['length'] + grid_size, grid_size):
        fig.add_shape(
            type="line",
            x0=0, y0=y, x1=ship_layout['width'], y1=y,
            line=dict(color="rgba(0,0,0,0.1)", width=1, dash="dash"),
            layer='below'
        )
    
    # Tambahkan titik-titik untuk setiap kendaraan
    all_dots_x = []
    all_dots_y = []
    all_dots_color = []
    all_dots_text = []
    all_dots_size = []
    
    for vehicle in vehicles:
        # Generate titik-titik dalam area kendaraan
        num_points = max(5, int(vehicle['length'] * vehicle['width'] * 0.5))  # Lebih banyak titik untuk area yang lebih besar
        
        # Titik acak dalam area kendaraan
        dots_x = []
        dots_y = []
        
        # Buat pola titik yang lebih terstruktur
        # Gunakan grid kecil dalam area kendaraan
        dot_spacing = min(0.5, max(0.2, min(vehicle['length'], vehicle['width']) / 5))
        
        # Titik-titik grid
        for i in np.arange(0, vehicle['length'], dot_spacing):
            for j in np.arange(0, vehicle['width'], dot_spacing):
                # Tambahkan sedikit variasi acak
                x_pos = vehicle['x'] + j + random.uniform(-0.05, 0.05)
                y_pos = vehicle['y'] + i + random.uniform(-0.05, 0.05)
                
                # Pastikan titik berada dalam area kendaraan
                if (vehicle['x'] <= x_pos <= vehicle['x'] + vehicle['width'] and 
                    vehicle['y'] <= y_pos <= vehicle['y'] + vehicle['length']):
                    dots_x.append(x_pos)
                    dots_y.append(y_pos)
        
        # Jika terlalu sedikit titik, tambahkan lebih banyak
        if len(dots_x) < 5:
            for _ in range(10):
                dots_x.append(vehicle['x'] + random.uniform(0, vehicle['width']))
                dots_y.append(vehicle['y'] + random.uniform(0, vehicle['length']))
        
        all_dots_x.extend(dots_x)
        all_dots_y.extend(dots_y)
        all_dots_color.extend([vehicle['color']] * len(dots_x))
        
        # Ukuran titik berdasarkan ukuran kendaraan
        base_size = max(5, min(15, (vehicle['length'] * vehicle['width']) ** 0.5 * 3))
        all_dots_size.extend([base_size] * len(dots_x))
        
        # Teks hover
        vehicle_text = f"{vehicle['name']}<br>{vehicle['length']}m × {vehicle['width']}m"
        all_dots_text.extend([vehicle_text] * len(dots_x))
    
    # Tambahkan semua titik ke plot
    if all_dots_x:
        fig.add_trace(go.Scatter(
            x=all_dots_x,
            y=all_dots_y,
            mode='markers',
            marker=dict(
                color=all_dots_color,
                size=all_dots_size,
                line=dict(width=1, color='white')
            ),
            text=all_dots_text,
            hoverinfo='text',
            name='Kendaraan',
            showlegend=False
        ))
    
    # Tambahkan titik pusat untuk setiap kendaraan dengan ikon
    for vehicle in vehicles:
        center_x = vehicle['x'] + vehicle['width'] / 2
        center_y = vehicle['y'] + vehicle['length'] / 2
        
        # Titik pusat yang lebih besar
        fig.add_trace(go.Scatter(
            x=[center_x],
            y=[center_y],
            mode='markers+text',
            marker=dict(
                color=darken_color(vehicle['color'], 30),
                size=30,
                symbol='circle',
                line=dict(width=2, color='white')
            ),
            text=[vehicle['icon']],
            textfont=dict(size=14, color='white'),
            textposition='middle center',
            showlegend=False,
            hoverinfo='none'
        ))
    
    # Highlight kendaraan yang dipilih
    if st.session_state.selected_vehicle:
        vehicle = st.session_state.selected_vehicle
        
        # Garis outline untuk kendaraan yang dipilih
        x0 = vehicle['x']
        y0 = vehicle['y']
        x1 = vehicle['x'] + vehicle['width']
        y1 = vehicle['y'] + vehicle['length']
        
        fig.add_trace(go.Scatter(
            x=[x0, x1, x1, x0, x0],
            y=[y0, y0, y1, y1, y0],
            mode='lines',
            line=dict(color='yellow', width=4, dash='dash'),
            fill='none',
            showlegend=False,
            hoverinfo='none'
        ))
        
        # Titik tambahan untuk highlight
        fig.add_trace(go.Scatter(
            x=[vehicle['x'] + vehicle['width']/2],
            y=[vehicle['y'] + vehicle['length']/2],
            mode='markers',
            marker=dict(
                color='yellow',
                size=40,
                symbol='circle-open',
                line=dict(width=3, color='yellow')
            ),
            showlegend=False,
            hoverinfo='none'
        ))
    
    # Konfigurasi layout
    fig.update_layout(
        title=f"Layout Kapal - Visualisasi Titik ({ship_layout['length']}m × {ship_layout['width']}m)",
        xaxis_title="Lebar Kapal (meter)",
        yaxis_title="Panjang Kapal (meter)",
        width=800,
        height=500,
        xaxis=dict(
            range=[-1, ship_layout['width'] + 1],
            gridcolor="rgba(0,0,0,0.2)",
            showgrid=True,
            dtick=5,
            tick0=0,
            tickfont=dict(size=12)
        ),
        yaxis=dict(
            range=[-1, ship_layout['length'] + 1],
            gridcolor="rgba(0,0,0,0.2)",
            showgrid=True,
            dtick=5,
            tick0=0,
            tickfont=dict(size=12)
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode='closest'
    )
    
    # Pastikan skala proporsional
    fig.update_xaxes(constrain='domain', scaleratio=1)
    fig.update_yaxes(constrain='domain', scaleratio=1)
    
    return fig

# Fungsi untuk ekspor layout ke JSON
def export_layout():
    export_data = {
        'ship_layout': st.session_state.ship_layout,
        'vehicles': st.session_state.vehicles,
        'next_vehicle_id': st.session_state.next_vehicle_id,
        'max_vehicles': st.session_state.max_vehicles
    }
    return json.dumps(export_data, indent=2)

# Fungsi untuk impor layout dari JSON
def import_layout(json_str):
    try:
        import_data = json.loads(json_str)
        st.session_state.ship_layout = import_data.get('ship_layout', st.session_state.ship_layout)
        st.session_state.vehicles = import_data.get('vehicles', [])
        st.session_state.next_vehicle_id = import_data.get('next_vehicle_id', st.session_state.next_vehicle_id + 1)
        st.session_state.max_vehicles = import_data.get('max_vehicles', st.session_state.max_vehicles)
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
        min_value=10.0, max_value=200.0, value=float(st.session_state.ship_layout['length']), 
        step=0.5, key="ship_length_input", format="%.1f"
    )
    
    ship_width = st.number_input(
        "Lebar Kapal (meter):", 
        min_value=5.0, max_value=50.0, value=float(st.session_state.ship_layout['width']), 
        step=0.5, key="ship_width_input", format="%.1f"
    )
    
    # Pengaturan jumlah maksimum kendaraan
    st.markdown("---")
    st.markdown("### 📊 Pengaturan Kendaraan")
    
    max_vehicles = st.number_input(
        "Maksimum Jumlah Kendaraan:", 
        min_value=1, max_value=100, value=st.session_state.max_vehicles, key="max_vehicles_input"
    )
    
    # Tambahkan pengaturan visualisasi
    st.markdown("---")
    st.markdown("### 🎨 Pengaturan Visualisasi")
    
    dot_density = st.slider(
        "Kepadatan Titik:", 
        min_value=1, max_value=10, value=5,
        help="Mengatur seberapa padat titik-titik dalam visualisasi"
    )
    
    dot_size = st.slider(
        "Ukuran Titik:", 
        min_value=3, max_value=15, value=8,
        help="Mengatur ukuran titik-titik dalam visualisasi"
    )
    
    if st.button("🔄 Update Layout Kapal", use_container_width=True):
        st.session_state.ship_layout = {
            'length': float(ship_length),
            'width': float(ship_width)
        }
        st.session_state.max_vehicles = max_vehicles
        
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
    
    # Kendaraan default
    if st.button(f"🏍️ Motor (2.0m × 0.8m)", 
                use_container_width=True, 
                help="Motor: Panjang 2.0m, Lebar 0.8m"):
        add_vehicle("Motor", 2.0, 0.8, "motor", "🏍️")
        st.rerun()
    
    if st.button(f"🚗 Mobil Kecil (4.5m × 1.8m)", 
                use_container_width=True, 
                help="Mobil Kecil: Panjang 4.5m, Lebar 1.8m"):
        add_vehicle("Mobil Kecil", 4.5, 1.8, "car", "🚗")
        st.rerun()
    
    if st.button(f"🚙 Mobil Sedang (5.0m × 2.0m)", 
                use_container_width=True, 
                help="Mobil Sedang: Panjang 5.0m, Lebar 2.0m"):
        add_vehicle("Mobil Sedang", 5.0, 2.0, "car", "🚙")
        st.rerun()
    
    if st.button(f"🚚 Truk (10.0m × 2.5m)", 
                use_container_width=True, 
                help="Truk: Panjang 10.0m, Lebar 2.5m"):
        add_vehicle("Truk", 10.0, 2.5, "truck", "🚚")
        st.rerun()
    
    if st.button(f"🚌 Bus (12.0m × 2.5m)", 
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
    st.markdown("### 🗺️ Layout Kapal - Visualisasi Titik")
    
    # Visualisasi kapal dengan titik-titik
    fig = create_ship_dots_visualization()
    st.plotly_chart(fig, use_container_width=True)
    
    # Statistik kapal
    stats = calculate_statistics()
    
    # Meter kapasitas kendaraan
    st.markdown(f"**Kapasitas Kendaraan:** {len(st.session_state.vehicles)}/{st.session_state.max_vehicles}")
    capacity_color = "green" if stats['capacity_percentage'] < 80 else "orange" if stats['capacity_percentage'] < 95 else "red"
    st.markdown(f"""
    <div class="capacity-meter">
        <div class="capacity-fill" style="width: {stats['capacity_percentage']}%; background-color: {capacity_color};"></div>
    </div>
    """, unsafe_allow_html=True)
    
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    with col_stat1:
        st.metric("Jumlah Kendaraan", stats['vehicle_count'])
    
    with col_stat2:
        st.metric("Luas Terpakai", f"{stats['used_area']:.1f} m²")
    
    with col_stat3:
        st.metric("Penggunaan Kapal", f"{stats['usage_percentage']:.1f}%")
    
    with col_stat4:
        free_area = stats['ship_area'] - stats['used_area']
        st.metric("Sisa Luas", f"{free_area:.1f} m²")
    
    # Informasi visualisasi
    with st.expander("ℹ️ Informasi Visualisasi Titik"):
        st.write("**Visualisasi Titik:**")
        st.write("- Setiap titik mewakili area kendaraan")
        st.write("- Titik-titik dengan warna sama = satu kendaraan")
        st.write("- Titik besar di tengah = pusat kendaraan dengan ikon")
        st.write("- Area kuning = kendaraan yang sedang dipilih")
        st.write("- Grid garis putus-putus = pembagi 5 meter")
        
        if st.session_state.vehicles:
            st.write("**Legenda Warna:**")
            for vehicle in st.session_state.vehicles[:6]:  # Tampilkan maksimal 6 warna
                st.markdown(f"""
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <div class="vehicle-color-box" style="background-color: {vehicle['color']};"></div>
                    <span>{vehicle['name']} ({vehicle['icon']})</span>
                </div>
                """, unsafe_allow_html=True)
    
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
    
    # Kontrol kendaraan
    st.markdown("### 🎮 Kontrol Kendaraan")
    
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
        
        # Tombol hapus
        if st.button("🗑️ Hapus Kendaraan", type="secondary", use_container_width=True):
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
            <h4 style="margin-top: 0; color: #1a2980;">{vehicle['icon']} {vehicle['name']}</h4>
            <p><strong>Tipe:</strong> {vehicle['type'].capitalize()}</p>
            <p><strong>Ukuran:</strong> {vehicle['length']}m × {vehicle['width']}m</p>
            <p><strong>Posisi:</strong> X={vehicle['x']:.1f}m, Y={vehicle['y']:.1f}m</p>
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
st.markdown("### 📖 Cara Menggunakan Visualisasi Titik:")
st.markdown("""
1. **Setiap titik mewakili area** dalam kendaraan
2. **Warna titik menunjukkan kendaraan** yang berbeda
3. **Titik besar di tengah** dengan ikon = pusat kendaraan
4. **Grid garis putus-putus** = pembagi setiap 5 meter
5. **Area kuning** = kendaraan yang sedang dipilih
6. **Skala proporsional** dengan ukuran sebenarnya

**Cara Mengatur Layout:**
1. **Atur ukuran kapal** di panel kiri
2. **Tambahkan kendaraan** dengan tombol atau kendaraan kustom
3. **Pilih kendaraan** untuk mengontrolnya
4. **Atur posisi** dengan koordinat manual atau tombol arah
5. **Pantau statistik** penggunaan ruang

**Tips Visualisasi Titik:**
- Titik lebih padat = area kendaraan lebih besar
- Titik dengan warna sama = kendaraan yang sama
- Hover pada titik untuk melihat detail kendaraan
- Kendaraan yang dipilih memiliki outline kuning
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
    - **Total Kendaraan:** {len(st.session_state.vehicles)} dari {st.session_state.max_vehicles} maksimum
    - **Total Luas Terpakai:** {total_area:.1f} m² dari {ship_area:.1f} m² ({total_area/ship_area*100:.1f}%)
    - **Motor:** {stats['vehicle_types'].get('motor', 0)} unit
    - **Mobil:** {stats['vehicle_types'].get('car', 0)} unit
    - **Truk:** {stats['vehicle_types'].get('truck', 0)} unit
    - **Bus:** {stats['vehicle_types'].get('bus', 0)} unit
    - **Kustom:** {stats['vehicle_types'].get('custom', 0)} unit
    """)
