"""
Management command to add placeholder images for books without cover images.
This creates simple placeholder images that can be replaced later.
"""
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont
import io
from library.models import Book
import os


class Command(BaseCommand):
    help = 'Add placeholder cover images for books that don\'t have images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing images with placeholders',
        )

    def handle(self, *args, **options):
        books_without_images = Book.objects.filter(cover_image='')
        if options['overwrite']:
            books_without_images = Book.objects.all()
        else:
            books_without_images = Book.objects.filter(cover_image='')

        if not books_without_images.exists():
            self.stdout.write(
                self.style.SUCCESS('All books already have cover images!')
            )
            return

        self.stdout.write(f'Creating placeholder images for {books_without_images.count()} books...')

        created_count = 0
        for book in books_without_images:
            try:
                # Create a placeholder image
                img = self.create_placeholder_image(book.title)
                
                # Save to the book's cover_image field
                img_io = io.BytesIO()
                img.save(img_io, format='JPEG', quality=85)
                img_file = ContentFile(img_io.getvalue())
                
                # Generate filename
                filename = f"book_{book.id}_placeholder.jpg"
                book.cover_image.save(filename, img_file, save=True)
                
                created_count += 1
                self.stdout.write(f'  [OK] Created image for: {book.title}')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  [ERROR] Error creating image for {book.title}: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully created {created_count} placeholder images!'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                '\nNote: These are placeholder images. You can replace them with actual book covers '
                'through the admin interface at /admin/library/book/'
            )
        )

    def create_placeholder_image(self, title):
        """Create a simple placeholder image with the book title"""
        # Image dimensions (typical book cover aspect ratio)
        width, height = 300, 400
        img = Image.new('RGB', (width, height), color='#4A90E2')
        draw = ImageDraw.Draw(img)

        # Draw a border
        draw.rectangle([10, 10, width-10, height-10], outline='white', width=3)

        # Try to use a font, fallback to default if not available
        try:
            # Try to use a larger font
            font_size = 24
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 24)
            except:
                font = ImageFont.load_default()

        # Split title into lines if too long
        words = title.split()
        lines = []
        current_line = []
        max_chars_per_line = 20

        for word in words:
            test_line = ' '.join(current_line + [word])
            if len(test_line) <= max_chars_per_line:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))

        # Limit to 3 lines
        lines = lines[:3]
        if len(lines) > 3:
            lines[2] = lines[2][:17] + '...'

        # Draw text (centered)
        y_offset = height // 2 - (len(lines) * 30) // 2
        for i, line in enumerate(lines):
            # Calculate text width for centering
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            y = y_offset + (i * 35)
            draw.text((x, y), line, fill='white', font=font)

        # Add "BOOK COVER" text at bottom
        try:
            small_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
        except:
            small_font = ImageFont.load_default()
        
        bottom_text = "BOOK COVER"
        bbox = draw.textbbox((0, 0), bottom_text, font=small_font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        draw.text((x, height - 40), bottom_text, fill='white', font=small_font)

        return img

