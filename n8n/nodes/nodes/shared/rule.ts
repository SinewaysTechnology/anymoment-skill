import type { IDataObject } from 'n8n-workflow';

/** Monthly recurrence. POST /events examples use 1 for weekly and 4 for once. */
export const MONTHLY_RECURRENCE = 2;

export type MonthlyType = 'last_business_day' | 'nth_business_day' | 'day_of_month' | 'day_of_week';

export type BusinessDayInput = {
	name: string;
	description: string;
	timezone: string;
	startTime: string;
	interval: number;
	monthlyType: MonthlyType;
	n: number;
	fromEnd: boolean;
	day: number;
	dayOfWeek: number;
	weekOfMonth: number;
	roll: string;
	country: string;
	subdiv: string;
	weekendDays: number[];
	closures: string;
	extraWorkdays: string;
};

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const TIME_PATTERN = /^\d{2}:\d{2}$/;
const DEFAULT_WEEKEND = [5, 6];

export function parseDateList(value: string, label: string): string[] {
	const dates = value
		.split(',')
		.map((part) => part.trim())
		.filter(Boolean);
	for (const date of dates) {
		if (!DATE_PATTERN.test(date)) {
			throw new Error(`${label} must be comma-separated YYYY-MM-DD dates. "${date}" is not.`);
		}
	}
	return dates;
}

export function sameNumberSet(left: number[], right: number[]): boolean {
	if (left.length !== right.length) return false;
	const sortedLeft = [...left].sort((a, b) => a - b);
	const sortedRight = [...right].sort((a, b) => a - b);
	return sortedLeft.every((value, index) => value === sortedRight[index]);
}

export function buildBusinessCalendar(input: BusinessDayInput): IDataObject | undefined {
	const country = input.country.trim();
	const subdiv = input.subdiv.trim();
	const closures = parseDateList(input.closures, 'Closures');
	const extraWorkdays = parseDateList(input.extraWorkdays, 'Extra workdays');
	const weekend = [...input.weekendDays].sort((a, b) => a - b);
	const customWeekend = !sameNumberSet(weekend, DEFAULT_WEEKEND);
	if (!country && !subdiv && !closures.length && !extraWorkdays.length && !customWeekend) {
		return undefined;
	}
	const calendar: IDataObject = {};
	if (country) calendar.country = country;
	if (subdiv) calendar.subdiv = subdiv;
	if (customWeekend || weekend.length) calendar.weekend_days = weekend;
	if (closures.length) calendar.closures = closures;
	if (extraWorkdays.length) calendar.extra_workdays = extraWorkdays;
	return calendar;
}

export function buildMonthlyConfig(input: BusinessDayInput): IDataObject {
	const config: IDataObject = {
		interval: input.interval,
		type: input.monthlyType,
	};
	if (input.monthlyType === 'nth_business_day') {
		config.n = input.n;
		config.from_end = input.fromEnd;
	}
	if (input.monthlyType === 'day_of_month') {
		config.day = input.day;
	}
	if (input.monthlyType === 'day_of_week') {
		config.day_of_week = input.dayOfWeek;
		config.week_of_month = input.weekOfMonth;
	}
	return config;
}

export function buildRuleBody(input: BusinessDayInput): IDataObject {
	if (!input.name.trim()) {
		throw new Error('Rule name is required.');
	}
	if (!TIME_PATTERN.test(input.startTime)) {
		throw new Error('Start time must be HH:MM in 24-hour form.');
	}
	if (!input.timezone.trim()) {
		throw new Error('Time zone is required. Use an IANA name such as Europe/Madrid or UTC.');
	}
	if (!Number.isInteger(input.interval) || input.interval < 1) {
		throw new Error('Interval must be a whole number of 1 or more.');
	}
	const body: IDataObject = {
		name: input.name.trim(),
		roll: input.roll,
		components: [
			{
				operator: 'OR',
				event_config: {
					recurrence: MONTHLY_RECURRENCE,
					start_time: input.startTime,
					timezone: input.timezone.trim(),
					is_all_day: false,
					config: buildMonthlyConfig(input),
				},
			},
		],
	};
	if (input.description.trim()) body.description = input.description.trim();
	const calendar = buildBusinessCalendar(input);
	if (calendar) body.business_calendar = calendar;
	return body;
}

export function numberList(value: unknown): number[] {
	const source = Array.isArray(value) ? value : [];
	return source.map((item) => Number(item)).filter((item) => Number.isInteger(item));
}

export function readBusinessDayInput(
	get: (name: string, fallback?: unknown) => unknown,
): BusinessDayInput {
	return {
		name: String(get('ruleName', '') ?? ''),
		description: String(get('ruleDescription', '') ?? ''),
		timezone: String(get('timezone', 'UTC') ?? 'UTC'),
		startTime: String(get('startTime', '09:00') ?? '09:00'),
		interval: Number(get('interval', 1)),
		monthlyType: String(get('monthlyType', 'last_business_day')) as MonthlyType,
		n: Number(get('nth', 1)),
		fromEnd: Boolean(get('fromEnd', false)),
		day: Number(get('day', 31)),
		dayOfWeek: Number(get('dayOfWeek', 0)),
		weekOfMonth: Number(get('weekOfMonth', 1)),
		roll: String(get('roll', 'none') ?? 'none'),
		country: String(get('country', '') ?? ''),
		subdiv: String(get('subdiv', '') ?? ''),
		weekendDays: numberList(get('weekendDays', [5, 6])),
		closures: String(get('closures', '') ?? ''),
		extraWorkdays: String(get('extraWorkdays', '') ?? ''),
	};
}
