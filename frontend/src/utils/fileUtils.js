// @/utils/fileUtils.js

/**
 * Обрабатывает файл и возвращает его в формате base64 с метаданными
 * @param {File} file - Объект File
 * @param {Object} options - Опции для изображений
 * @param {number} options.maxWidth - Максимальная ширина изображения
 * @param {number} options.quality - Качество изображения (0-1)
 * @returns {Promise<{base64: string, meta: {name: string, size: number, type: string}}>}
 */
export async function processFile(file, options = {}) {
	return new Promise((resolve, reject) => {
		// Для изображений используем canvas для сжатия
		if (file.type.startsWith('image/') && (options.maxWidth || options.quality)) {
			const img = new Image();
			const url = URL.createObjectURL(file);

			img.onload = () => {
				URL.revokeObjectURL(url);

				try {
					const canvas = document.createElement('canvas');
					const ctx = canvas.getContext('2d');

					// Рассчитываем новые размеры
					const maxWidth = options.maxWidth || img.width;
					const scaleFactor = maxWidth / img.width;
					const newWidth = maxWidth;
					const newHeight = img.height * scaleFactor;

					canvas.width = newWidth;
					canvas.height = newHeight;
					ctx.drawImage(img, 0, 0, newWidth, newHeight);

					// Конвертируем в base64 с заданным качеством
					const quality = options.quality ?? 0.8;
					canvas.toBlob(blob => {
						const reader = new FileReader();
						reader.onload = () => resolve({
							base64: reader.result.split(',')[1],
							meta: {
								name: file.name,
								size: blob.size,
								type: file.type
							}
						});
						reader.onerror = reject;
						reader.readAsDataURL(blob);
					}, file.type, quality);
				} catch (error) {
					reject(error);
				}
			};

			img.onerror = () => {
				URL.revokeObjectURL(url);
				reject(new Error('Ошибка загрузки изображения'));
			};

			img.src = url;
		} else {
			// Для обычных файлов
			const reader = new FileReader();
			reader.onload = () => resolve({
				base64: reader.result.split(',')[1],
				meta: {
					name: file.name,
					size: file.size,
					type: file.type
				}
			});
			reader.onerror = reject;
			reader.readAsDataURL(file);
		}
	});
}