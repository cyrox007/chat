/**
 * Преобразует строку UTC (без 'Z') в локальное время пользователя
 * @param {string} utcString - Строка даты в формате UTC (например "2025-04-23T18:34:07")
 * @param {Object} [options] - Дополнительные параметры форматирования
 * @param {boolean} [options.showSeconds=false] - Показывать секунды
 * @param {boolean} [options.showDate=true] - Показывать дату
 * @returns {string} Отформатированная строка локального времени
 */
export function formatUTCDate(utcString, options = {}) {
	if (!utcString) return '';

	const defaults = {
		showSeconds: false,
		showDate: true
	};
	const config = { ...defaults, ...options };

	try {
		// Добавляем 'Z' для явного указания UTC, если его нет
		const date = new Date(utcString.endsWith('Z') ? utcString : `${utcString}Z`);

		// Проверка на валидность даты
		if (isNaN(date.getTime())) {
			console.warn('Invalid date string:', utcString);
			return utcString;
		}

		// Форматируем дату и время
		const timeFormatter = new Intl.DateTimeFormat(undefined, {
			hour: '2-digit',
			minute: '2-digit',
			second: config.showSeconds ? '2-digit' : undefined,
			hour12: false
		});

		const dateFormatter = new Intl.DateTimeFormat(undefined, {
			day: '2-digit',
			month: '2-digit',
			year: 'numeric'
		});

		const timeStr = timeFormatter.format(date);
		const dateStr = dateFormatter.format(date);

		return config.showDate
			? `${dateStr}, ${timeStr}`
			: timeStr;

	} catch (error) {
		console.error('Error formatting date:', error);
		return utcString;
	}
}

/**
 * Альтернативный вариант - форматирование вручную
 * @param {string} utcString - Строка даты в UTC
 * @returns {string} Локализованная строка даты и времени
 */
export function formatUTCDateManual(utcString) {
	if (!utcString) return '';

	try {
		const date = new Date(utcString.endsWith('Z') ? utcString : `${utcString}Z`);

		if (isNaN(date.getTime())) {
			return utcString;
		}

		// Получаем локальные компоненты даты
		const pad = num => num.toString().padStart(2, '0');

		const day = pad(date.getDate());
		const month = pad(date.getMonth() + 1);
		const year = date.getFullYear();
		const hours = pad(date.getHours());
		const minutes = pad(date.getMinutes());

		return `${day}.${month}.${year}, ${hours}:${minutes}`;
	} catch (error) {
		console.error('Error formatting date:', error);
		return utcString;
	}
}