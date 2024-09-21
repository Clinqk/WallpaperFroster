import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk, ImageFilter, ImageEnhance
import cupy as cp
from idlelib.tooltip import Hovertip
import os
import math

class ImageEditor:
    def __init__(self, master):
        self.master = master
        self.master.title("Wallpaper Froster")
        self.master.geometry("1000x700")
        self.custom_font = ('Helvetica', 10)
        self.colors = {
            'bg': '#f0f0f0',
            'fg': '#333333',
            'accent': '#4a90e2'
        }

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=self.colors['bg'])
        style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['fg'], font=self.custom_font)
        style.configure('TButton', background=self.colors['accent'], foreground='white', font=self.custom_font)
        style.configure('TScale', background=self.colors['bg'])
        style.configure('TEntry', font=self.custom_font)

        self.master.configure(bg=self.colors['bg'])

        self.image = None
        self.current_image = None
        self.photo = None
        self.zoom_factor = 1.0
        self.zoom_entry = None
        self.original_filename = None
        self.cache = {}  # Add cache dictionary

        self.create_widgets()

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas frame (left side)
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Canvas
        self.canvas = tk.Canvas(canvas_frame, bg='#ffffff', highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind mouse wheel event for scrolling
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)
        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)

        # Controls frame (right side)
        controls_frame = ttk.Frame(main_frame, padding="10")
        controls_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="Load Image", command=self.load_image).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(button_frame, text="Save Image", command=self.save_image).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(button_frame, text="Reset All", command=self.reset_all).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Separator(controls_frame, orient='horizontal').pack(fill='x', pady=10)

        # Zoom controls
        zoom_frame = ttk.LabelFrame(controls_frame, text="Zoom", padding="5 5 5 5")
        zoom_frame.pack(fill=tk.X, pady=10)
        ttk.Button(zoom_frame, text="-", command=self.zoom_out, width=2).pack(side=tk.LEFT)
        ttk.Button(zoom_frame, text="+", command=self.zoom_in, width=2).pack(side=tk.RIGHT)
        self.zoom_scale = ttk.Scale(zoom_frame, from_=10, to=200, orient=tk.HORIZONTAL, command=self.update_zoom)
        self.zoom_scale.set(100)
        self.zoom_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))
        self.zoom_entry = ttk.Entry(zoom_frame, width=5, font=self.custom_font)
        self.zoom_entry.pack(side=tk.LEFT)
        self.zoom_entry.insert(0, "100")
        self.zoom_entry.bind('<Return>', lambda event: self.set_zoom_value())
        self.zoom_reset = ttk.Button(zoom_frame, text="↺", width=3, command=self.reset_zoom)
        self.zoom_reset.pack(side=tk.LEFT, padx=(5, 0))
        Hovertip(self.zoom_reset, "Reset zoom to 100%")

        ttk.Separator(controls_frame, orient='horizontal').pack(fill='x', pady=10)

        # Sliders
        sliders = [
            ("Blur", 0, 500, 0.1, 100),
            ("Brightness", 0.1, 2.0, 0.1, 1.0),
            ("Contrast", 0.1, 2.0, 0.1, 1.1),
            ("Saturation", 0.0, 2.0, 0.1, 1.1),
            ("Grain Strength", 0, 25, 1, 3.5),
            ("Speckle Noise", 0, 0.25, 0.01, 0),
            ("Poisson Noise", 0, 0.4, 0.01, 0),
            ("Film Grain", 0, 25, 1, 2.5),
            ("Color Mix", 0, 200, 1, 30),
            ("Color Mix Strength", 1, 200, 1, 20),
            ("Color Temperature", 2000, 10000, 100, 6500),
            ("Vignette", 0, 1, 0.01, 0.1),
        ]
        for slider in sliders:
            self.create_scale(controls_frame, *slider)

    def create_scale(self, parent, label, from_, to, resolution, default=None):
        frame = ttk.Frame(parent, padding="3 3 3 3")
        frame.pack(fill=tk.X, pady=0)
        ttk.Label(frame, text=label, width=16, font=self.custom_font).pack(side=tk.LEFT)
        scale = ttk.Scale(frame, from_=from_, to=to, orient=tk.HORIZONTAL, command=self.update_image)
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))
        entry = ttk.Entry(frame, width=5, font=self.custom_font)
        entry.pack(side=tk.LEFT)
        entry.bind('<Return>', lambda event, s=scale, e=entry: self.set_scale_value(s, e))
        reset_button = ttk.Button(frame, text="↺", width=3, command=lambda: self.reset_scale(scale, entry, default))
        reset_button.pack(side=tk.LEFT, padx=(5, 0))

        if default is not None:
            scale.set(default)
            entry.insert(0, str(default))

        scale_name = label.lower().replace(' ', '_')
        setattr(self, f"{scale_name}_scale", scale)
        setattr(self, f"{scale_name}_entry", entry)

        Hovertip(scale, f"Adjust {label}")
        Hovertip(reset_button, f"Reset {label} to default")

    def reset_scale(self, scale, entry, default_value):
        scale.set(default_value)
        entry.delete(0, tk.END)
        entry.insert(0, str(default_value))
        self.update_image()

    def set_scale_value(self, scale, entry):
        try:
            value = float(entry.get())
            scale.set(value)
            self.update_image()
        except ValueError:
            pass

    def _on_mousewheel(self, event):
        if event.state & 0x4:  # Check if Ctrl key is pressed
            self._zoom_mousewheel(event)
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_shift_mousewheel(self, event):
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def _start_drag(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def _drag(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _zoom_mousewheel(self, event):
        current_zoom = self.zoom_scale.get()
        if event.delta > 0:
            new_zoom = min(current_zoom * 1.1, 200)
        else:
            new_zoom = max(current_zoom / 1.1, 10)
        self.zoom_scale.set(new_zoom)
        self.update_zoom()

    def load_image(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            try:
                self.image = Image.open(file_path).convert('RGB')
                self.zoom_factor = 1.0
                self.zoom_scale.set(100)
                self.original_filename = os.path.splitext(os.path.basename(file_path))[0]
                self.cache.clear()  # Clear cache when loading a new image
                self.update_image()
            except Exception as e:
                print(f"Error loading image: {e}")

    def save_image(self):
        if self.current_image and self.original_filename:
            default_name = f"{self.original_filename}_frosted.png"
            file_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                     filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
                                                     initialfile=default_name)
            if file_path:
                self.current_image.save(file_path)

    def zoom_in(self):
        current_zoom = self.zoom_scale.get()
        new_zoom = min(current_zoom * 1.2, 200)
        self.zoom_scale.set(new_zoom)
        self.update_zoom()

    def zoom_out(self):
        current_zoom = self.zoom_scale.get()
        new_zoom = max(current_zoom / 1.2, 10)
        self.zoom_scale.set(new_zoom)
        self.update_zoom()

    def update_zoom(self, *args):
        zoom_value = self.zoom_scale.get()
        self.zoom_factor = zoom_value / 100
        if self.zoom_entry:
            self.zoom_entry.delete(0, tk.END)
            self.zoom_entry.insert(0, f"{zoom_value:.0f}")
        self.update_image()

    def set_zoom_value(self):
        try:
            zoom_value = float(self.zoom_entry.get())
            if 10 <= zoom_value <= 200:
                self.zoom_scale.set(zoom_value)
                self.update_zoom()
        except ValueError:
            pass

    def reset_zoom(self):
        self.zoom_scale.set(100)
        self.update_zoom()

    def add_grain(self, image, strength):
        img_array = cp.array(image)
        noise = cp.random.normal(0, strength, img_array.shape)
        noisy_img_array = cp.clip(img_array.astype(cp.float32) + noise, 0, 255).astype(cp.uint8)
        return Image.fromarray(cp.asnumpy(noisy_img_array))

    def add_speckle(self, image, intensity):
        img_array = cp.array(image)
        noise = cp.random.normal(0, intensity, img_array.shape)
        noisy_img = img_array + img_array * noise
        return Image.fromarray(cp.asnumpy(cp.clip(noisy_img, 0, 255).astype(cp.uint8)))

    def add_poisson(self, image, intensity):
        img_array = cp.array(image)
        noise = cp.random.poisson(img_array / 255.0 * 50.0 * intensity) / 50.0 * 255.0
        noisy_img = img_array + noise.astype(cp.uint8)
        return Image.fromarray(cp.asnumpy(cp.clip(noisy_img, 0, 255).astype(cp.uint8)))

    def add_film_grain(self, image, strength):
        img_array = cp.array(image)
        noise = cp.random.normal(0, strength, img_array.shape)
        noisy_img = img_array + noise
        return Image.fromarray(cp.asnumpy(cp.clip(noisy_img, 0, 255).astype(cp.uint8)))

    def add_coarse_grain(self, image, strength, size):
        img_array = cp.array(image)
        h, w, c = img_array.shape
        coarse_h = h // size + (1 if h % 10 else 0)
        coarse_w = w // size + (1 if w % 10 else 0)
        coarse_noise = cp.random.normal(0, strength, (coarse_h, coarse_w, c))
        coarse_noise = cp.repeat(cp.repeat(coarse_noise, size, axis=0), size, axis=1)
        coarse_noise = coarse_noise[:h, :w, :]
        noisy_img_array = cp.clip(img_array.astype(cp.float32) + coarse_noise, 0, 255).astype(cp.uint8)
        return Image.fromarray(cp.asnumpy(noisy_img_array))

    def adjust_color_temperature(self, image, temperature):
        temperature = temperature / 100
        if temperature <= 66:
            red = 255
        else:
            red = temperature - 60
            red = 329.698727446 * (red ** -0.1332047592)
        red = max(0, min(255, red))

        if temperature <= 66:
            green = temperature
            green = 99.4708025861 * math.log(green) - 161.1195681661
        else:
            green = temperature - 60
            green = 288.1221695283 * (green ** -0.0755148492)
        green = max(0, min(255, green))

        if temperature >= 66:
            blue = 255
        elif temperature <= 19:
            blue = 0
        else:
            blue = temperature - 10
            blue = 138.5177312231 * math.log(blue) - 305.0447927307
        blue = max(0, min(255, blue))

        # Create color balance filter
        r, g, b = red / 255, green / 255, blue / 255
        matrix = (r, 0, 0, 0,
                  0, g, 0, 0,
                  0, 0, b, 0)
        return image.convert('RGB', matrix)

    def add_vignette(self, image, strength):
        width, height = image.size
        center_x, center_y = width // 2, height // 2
        max_dist = math.sqrt(center_x**2 + center_y**2)
    
        img_array = cp.array(image)
        y, x = cp.ogrid[:height, :width]
        dist = cp.sqrt((x - center_x)**2 + (y - center_y)**2)
    
        vignette = 1 - (dist / max_dist) * strength
        vignette = cp.clip(vignette, 0, 1)
    
        vignette = cp.dstack([vignette] * 3)  # Apply to all color channels
        vignetted_img = cp.clip(img_array * vignette, 0, 255).astype(cp.uint8)
    
        return Image.fromarray(cp.asnumpy(vignetted_img))

    def apply_filters(self, img, params):
        img = self.add_coarse_grain(img, params['color_mix'], int(params['color_mix_strength']))
        img = ImageEnhance.Brightness(img).enhance(params['brightness'])
        img = ImageEnhance.Contrast(img).enhance(params['contrast'])
        img = ImageEnhance.Color(img).enhance(params['saturation'])
        img = self.adjust_color_temperature(img, params['color_temperature'])
        img = img.filter(ImageFilter.GaussianBlur(radius=params['blur']))
        img = self.add_grain(img, params['grain_strength'])
        img = self.add_speckle(img, params['speckle_noise'])
        img = self.add_poisson(img, params['poisson_noise'])
        img = self.add_film_grain(img, params['film_grain'])
        img = self.add_vignette(img, params['vignette'])
        return img

    def update_image(self, *args):
        if self.image:
            # Get current parameter values
            params = {
                'blur': self.blur_scale.get(),
                'brightness': self.brightness_scale.get(),
                'contrast': self.contrast_scale.get(),
                'saturation': self.saturation_scale.get(),
                'grain_strength': self.grain_strength_scale.get(),
                'speckle_noise': self.speckle_noise_scale.get(),
                'poisson_noise': self.poisson_noise_scale.get(),
                'film_grain': self.film_grain_scale.get(),
                'color_mix': self.color_mix_scale.get(),
                'color_mix_strength': self.color_mix_strength_scale.get(),
                'color_temperature': self.color_temperature_scale.get(),
                'vignette': self.vignette_scale.get()
            }

            # Check cache for existing results
            cache_key = tuple(params.items())
            if cache_key in self.cache:
                self.current_image = self.cache[cache_key]
            else:
                # Apply filters
                img = self.image.copy()
                img = self.apply_filters(img, params)
                self.current_image = img
                
                # Cache the result
                self.cache[cache_key] = img

            # Update preview
            self.update_preview()

    def update_preview(self):
        # Update entry values
        for attr in dir(self):
            if attr.endswith('_scale'):
                scale = getattr(self, attr)
                entry_attr = attr.replace('_scale', '_entry')
                if hasattr(self, entry_attr):
                    entry = getattr(self, entry_attr)
                    entry.delete(0, tk.END)
                    entry.insert(0, f"{scale.get():.2f}")

        # Resize for preview
        width, height = self.current_image.size
        new_width = int(width * self.zoom_factor)
        new_height = int(height * self.zoom_factor)
        preview_img = self.current_image.resize((new_width, new_height), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(preview_img)
        self.canvas.delete("all")
        self.canvas_image = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

        # Update scroll region
        self.canvas.config(scrollregion=self.canvas.bbox(self.canvas_image))

    def reset_all(self):
        default_values = {
            'blur': 100,
            'brightness': 1.0,
            'contrast': 1.1,
            'saturation': 1.1,
            'grain_strength': 3.5,
            'speckle_noise': 0,
            'poisson_noise': 0,
            'film_grain': 2.5,
            'color_mix': 30,
            'color_mix_strength': 20,
            'color_temperature': 6500,
            'vignette': 0.1
        }

        for attr, value in default_values.items():
            scale = getattr(self, f"{attr}_scale")
            entry = getattr(self, f"{attr}_entry")
            scale.set(value)
            entry.delete(0, tk.END)
            entry.insert(0, str(value))

        self.reset_zoom()
        self.cache.clear()  # Clear the cache
        self.update_image()

if __name__ == "__main__":
    root = tk.Tk()
    editor = ImageEditor(root)
    root.mainloop()
