import type { IDisplayOptions, INodeProperties } from 'n8n-workflow';

type Show = Record<string, string[]>;

function shown(base: Show, extra?: Show): IDisplayOptions {
	return { show: extra ? { ...base, ...extra } : base };
}

const dayOfWeekOptions = [
	{ name: 'Monday', value: 0 },
	{ name: 'Tuesday', value: 1 },
	{ name: 'Wednesday', value: 2 },
	{ name: 'Thursday', value: 3 },
	{ name: 'Friday', value: 4 },
	{ name: 'Saturday', value: 5 },
	{ name: 'Sunday', value: 6 },
];

export function calendarLocator(base: Show): INodeProperties {
	return {
		displayName: 'Calendar',
		name: 'calendarId',
		type: 'resourceLocator',
		default: { mode: 'list', value: '' },
		required: true,
		description:
			'Calendar that owns the subscription. API keys cannot create calendars, so create it in AnyMoment first. From List calls GET /calendars.',
		displayOptions: shown(base),
		modes: [
			{
				displayName: 'From List',
				name: 'list',
				type: 'list',
				typeOptions: {
					searchListMethod: 'searchCalendars',
					searchable: true,
				},
			},
			{
				displayName: 'By ID',
				name: 'id',
				type: 'string',
				placeholder: '00000000-0000-0000-0000-000000000000',
			},
		],
	};
}

export function eventLocator(base: Show, description: string): INodeProperties {
	return {
		displayName: 'Rule',
		name: 'eventId',
		type: 'resourceLocator',
		default: { mode: 'list', value: '' },
		required: true,
		description,
		displayOptions: shown(base),
		modes: [
			{
				displayName: 'From List',
				name: 'list',
				type: 'list',
				typeOptions: {
					searchListMethod: 'searchEvents',
					searchable: true,
				},
			},
			{
				displayName: 'By ID',
				name: 'id',
				type: 'string',
				placeholder: '00000000-0000-0000-0000-000000000000',
			},
		],
	};
}

export function businessDayFields(base: Show): INodeProperties[] {
	const nth = shown(base, { monthlyType: ['nth_business_day'] });
	const dayOfMonth = shown(base, { monthlyType: ['day_of_month'] });
	const dayOfWeek = shown(base, { monthlyType: ['day_of_week'] });
	return [
		{
			displayName: 'Rule Name',
			name: 'ruleName',
			type: 'string',
			default: 'Month-end close',
			required: true,
			description: 'Name stored on the AnyMoment event',
			displayOptions: shown(base),
		},
		{
			displayName: 'Description',
			name: 'ruleDescription',
			type: 'string',
			default: '',
			description: 'Optional description stored on the event',
			displayOptions: shown(base),
		},
		{
			displayName: 'Time Zone',
			name: 'timezone',
			type: 'string',
			default: 'UTC',
			placeholder: 'Europe/Madrid',
			required: true,
			description:
				'IANA time zone for the start time, such as Europe/Madrid or America/New_York. Instance times come back in UTC.',
			displayOptions: shown(base),
		},
		{
			displayName: 'Start Time',
			name: 'startTime',
			type: 'string',
			default: '09:00',
			placeholder: '09:00',
			required: true,
			description: 'Local time of day in HH:MM, 24-hour',
			displayOptions: shown(base),
		},
		{
			displayName: 'Interval (Months)',
			name: 'interval',
			type: 'number',
			default: 1,
			typeOptions: { minValue: 1, numberPrecision: 0 },
			description: 'Run every N months. 1 means every month.',
			displayOptions: shown(base),
		},
		{
			displayName: 'Monthly Type',
			name: 'monthlyType',
			type: 'options',
			default: 'last_business_day',
			noDataExpression: true,
			description: 'Which day inside each month the rule expands to',
			displayOptions: shown(base),
			options: [
				{
					name: 'Day of Month',
					value: 'day_of_month',
					description: 'A fixed calendar day, before roll is applied',
				},
				{
					name: 'Day of Week',
					value: 'day_of_week',
					description: 'A weekday in a given week of the month',
				},
				{
					name: 'Last Business Day',
					value: 'last_business_day',
					description: 'The last working day, skipping the weekend and holidays',
				},
				{
					name: 'Nth Business Day',
					value: 'nth_business_day',
					description: 'The first, second, or nth working day, from the start or the end',
				},
			],
		},
		{
			displayName: 'Which Business Day',
			name: 'nth',
			type: 'number',
			default: 1,
			typeOptions: { minValue: 1, maxValue: 31, numberPrecision: 0 },
			description: 'Which business day to use. 1 is the first. Required for nth business day.',
			displayOptions: nth,
		},
		{
			displayName: 'Count From the End',
			name: 'fromEnd',
			type: 'boolean',
			default: false,
			description:
				'Whether to count the business day from the end of the month. Used by nth business day.',
			displayOptions: nth,
		},
		{
			displayName: 'Day of Month',
			name: 'day',
			type: 'number',
			default: 31,
			typeOptions: { minValue: 1, maxValue: 31, numberPrecision: 0 },
			description: 'Calendar day from 1 to 31. Shorter months use the last day.',
			displayOptions: dayOfMonth,
		},
		{
			displayName: 'Day of Week',
			name: 'dayOfWeek',
			type: 'options',
			default: 0,
			description: 'Weekday used by the day-of-week monthly type. 0 is Monday and 6 is Sunday.',
			displayOptions: dayOfWeek,
			options: dayOfWeekOptions,
		},
		{
			displayName: 'Week of Month',
			name: 'weekOfMonth',
			type: 'options',
			default: 1,
			description: 'Which week of the month. 5 means the last week.',
			displayOptions: dayOfWeek,
			options: [
				{ name: 'First', value: 1 },
				{ name: 'Second', value: 2 },
				{ name: 'Third', value: 3 },
				{ name: 'Fourth', value: 4 },
				{ name: 'Last', value: 5 },
			],
		},
		{
			displayName: 'Roll',
			name: 'roll',
			type: 'options',
			default: 'none',
			description:
				'What to do after expansion when a date is not a business day. Last business day already lands on a working day, so leave this on none unless you start from a fixed day.',
			displayOptions: shown(base),
			options: [
				{ name: 'Backward', value: 'backward', description: 'Move to the previous business day' },
				{ name: 'Forward', value: 'forward', description: 'Move to the next business day' },
				{ name: 'Nearest', value: 'nearest', description: 'Move to the nearest business day' },
				{ name: 'None', value: 'none', description: 'Leave the date unchanged' },
				{ name: 'Skip', value: 'skip', description: 'Drop the date' },
			],
		},
		{
			displayName: 'Country',
			name: 'country',
			type: 'string',
			default: 'US',
			placeholder: 'GB',
			description:
				'ISO 3166-1 alpha-2 country code for the holiday calendar, such as US or GB. Clear it to skip public holidays.',
			displayOptions: shown(base),
		},
		{
			displayName: 'Subdivision',
			name: 'subdiv',
			type: 'string',
			default: '',
			placeholder: 'ENG',
			description:
				'Optional subdivision code understood by the holiday calendar, such as ENG or CA',
			displayOptions: shown(base),
		},
		{
			displayName: 'Weekend Days',
			name: 'weekendDays',
			type: 'multiOptions',
			default: [5, 6],
			description:
				'Days off. 0 is Monday and 6 is Sunday. Saturday and Sunday is the default. A custom set, such as Friday and Saturday, is sent as weekend_days.',
			displayOptions: shown(base),
			options: dayOfWeekOptions,
		},
		{
			displayName: 'Closures',
			name: 'closures',
			type: 'string',
			default: '',
			placeholder: '2026-12-24, 2026-12-31',
			description: 'Extra days off, comma-separated YYYY-MM-DD dates',
			displayOptions: shown(base),
		},
		{
			displayName: 'Extra Workdays',
			name: 'extraWorkdays',
			type: 'string',
			default: '',
			placeholder: '2026-12-26',
			description:
				'Working dates that override weekends, holidays, and closures. Comma-separated YYYY-MM-DD dates.',
			displayOptions: shown(base),
		},
	];
}
