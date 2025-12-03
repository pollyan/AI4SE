--
-- PostgreSQL database dump
--

\restrict RBOY5p7mBC8YdKEguhaKa5PSjhpnCRdW03I3wX0fKJaWu7hhgOB4ptOzPclkzRs

-- Dumped from database version 15.15
-- Dumped by pg_dump version 15.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: execution_history; Type: TABLE; Schema: public; Owner: intent_user
--

CREATE TABLE public.execution_history (
    id integer NOT NULL,
    execution_id character varying(50) NOT NULL,
    test_case_id integer NOT NULL,
    status character varying(50) NOT NULL,
    mode character varying(20),
    browser character varying(50),
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone,
    duration integer,
    steps_total integer,
    steps_passed integer,
    steps_failed integer,
    result_summary text,
    screenshots_path text,
    logs_path text,
    error_message text,
    error_stack text,
    executed_by character varying(100),
    created_at timestamp without time zone
);


ALTER TABLE public.execution_history OWNER TO intent_user;

--
-- Name: execution_history_id_seq; Type: SEQUENCE; Schema: public; Owner: intent_user
--

CREATE SEQUENCE public.execution_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.execution_history_id_seq OWNER TO intent_user;

--
-- Name: execution_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: intent_user
--

ALTER SEQUENCE public.execution_history_id_seq OWNED BY public.execution_history.id;


--
-- Name: execution_variables; Type: TABLE; Schema: public; Owner: intent_user
--

CREATE TABLE public.execution_variables (
    id integer NOT NULL,
    execution_id character varying(50) NOT NULL,
    variable_name character varying(255) NOT NULL,
    variable_value text,
    data_type character varying(50) NOT NULL,
    source_step_index integer NOT NULL,
    source_api_method character varying(100),
    source_api_params text,
    created_at timestamp without time zone,
    is_encrypted boolean
);


ALTER TABLE public.execution_variables OWNER TO intent_user;

--
-- Name: execution_variables_id_seq; Type: SEQUENCE; Schema: public; Owner: intent_user
--

CREATE SEQUENCE public.execution_variables_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.execution_variables_id_seq OWNER TO intent_user;

--
-- Name: execution_variables_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: intent_user
--

ALTER SEQUENCE public.execution_variables_id_seq OWNED BY public.execution_variables.id;


--
-- Name: requirements_ai_configs; Type: TABLE; Schema: public; Owner: intent_user
--

CREATE TABLE public.requirements_ai_configs (
    id integer NOT NULL,
    config_name character varying(255) NOT NULL,
    api_key text NOT NULL,
    base_url character varying(500) NOT NULL,
    model_name character varying(100) NOT NULL,
    is_default boolean,
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.requirements_ai_configs OWNER TO intent_user;

--
-- Name: requirements_ai_configs_id_seq; Type: SEQUENCE; Schema: public; Owner: intent_user
--

CREATE SEQUENCE public.requirements_ai_configs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.requirements_ai_configs_id_seq OWNER TO intent_user;

--
-- Name: requirements_ai_configs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: intent_user
--

ALTER SEQUENCE public.requirements_ai_configs_id_seq OWNED BY public.requirements_ai_configs.id;


--
-- Name: requirements_messages; Type: TABLE; Schema: public; Owner: intent_user
--

CREATE TABLE public.requirements_messages (
    id integer NOT NULL,
    session_id character varying(50) NOT NULL,
    message_type character varying(20) NOT NULL,
    content text NOT NULL,
    message_metadata text,
    attached_files text,
    created_at timestamp without time zone
);


ALTER TABLE public.requirements_messages OWNER TO intent_user;

--
-- Name: requirements_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: intent_user
--

CREATE SEQUENCE public.requirements_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.requirements_messages_id_seq OWNER TO intent_user;

--
-- Name: requirements_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: intent_user
--

ALTER SEQUENCE public.requirements_messages_id_seq OWNED BY public.requirements_messages.id;


--
-- Name: requirements_sessions; Type: TABLE; Schema: public; Owner: intent_user
--

CREATE TABLE public.requirements_sessions (
    id character varying(50) NOT NULL,
    project_name character varying(255),
    session_status character varying(50),
    current_stage character varying(50),
    user_context text,
    ai_context text,
    consensus_content text,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


ALTER TABLE public.requirements_sessions OWNER TO intent_user;

--
-- Name: step_executions; Type: TABLE; Schema: public; Owner: intent_user
--

CREATE TABLE public.step_executions (
    id integer NOT NULL,
    execution_id character varying(50) NOT NULL,
    step_index integer NOT NULL,
    step_description text NOT NULL,
    status character varying(20) NOT NULL,
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone,
    duration integer,
    screenshot_path text,
    ai_confidence double precision,
    ai_decision text,
    error_message text
);


ALTER TABLE public.step_executions OWNER TO intent_user;

--
-- Name: step_executions_id_seq; Type: SEQUENCE; Schema: public; Owner: intent_user
--

CREATE SEQUENCE public.step_executions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.step_executions_id_seq OWNER TO intent_user;

--
-- Name: step_executions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: intent_user
--

ALTER SEQUENCE public.step_executions_id_seq OWNED BY public.step_executions.id;


--
-- Name: templates; Type: TABLE; Schema: public; Owner: intent_user
--

CREATE TABLE public.templates (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    category character varying(100),
    steps_template text NOT NULL,
    parameters text,
    usage_count integer,
    created_by character varying(100),
    created_at timestamp without time zone,
    is_public boolean
);


ALTER TABLE public.templates OWNER TO intent_user;

--
-- Name: templates_id_seq; Type: SEQUENCE; Schema: public; Owner: intent_user
--

CREATE SEQUENCE public.templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.templates_id_seq OWNER TO intent_user;

--
-- Name: templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: intent_user
--

ALTER SEQUENCE public.templates_id_seq OWNED BY public.templates.id;


--
-- Name: test_cases; Type: TABLE; Schema: public; Owner: intent_user
--

CREATE TABLE public.test_cases (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    steps text NOT NULL,
    tags character varying(500),
    category character varying(100),
    priority integer,
    created_by character varying(100),
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_active boolean
);


ALTER TABLE public.test_cases OWNER TO intent_user;

--
-- Name: test_cases_id_seq; Type: SEQUENCE; Schema: public; Owner: intent_user
--

CREATE SEQUENCE public.test_cases_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.test_cases_id_seq OWNER TO intent_user;

--
-- Name: test_cases_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: intent_user
--

ALTER SEQUENCE public.test_cases_id_seq OWNED BY public.test_cases.id;


--
-- Name: variable_references; Type: TABLE; Schema: public; Owner: intent_user
--

CREATE TABLE public.variable_references (
    id integer NOT NULL,
    execution_id character varying(50) NOT NULL,
    step_index integer NOT NULL,
    variable_name character varying(255) NOT NULL,
    reference_path character varying(500),
    parameter_name character varying(255),
    original_expression character varying(500),
    resolved_value text,
    resolution_status character varying(20),
    error_message text,
    created_at timestamp without time zone
);


ALTER TABLE public.variable_references OWNER TO intent_user;

--
-- Name: variable_references_id_seq; Type: SEQUENCE; Schema: public; Owner: intent_user
--

CREATE SEQUENCE public.variable_references_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.variable_references_id_seq OWNER TO intent_user;

--
-- Name: variable_references_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: intent_user
--

ALTER SEQUENCE public.variable_references_id_seq OWNED BY public.variable_references.id;


--
-- Name: execution_history id; Type: DEFAULT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.execution_history ALTER COLUMN id SET DEFAULT nextval('public.execution_history_id_seq'::regclass);


--
-- Name: execution_variables id; Type: DEFAULT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.execution_variables ALTER COLUMN id SET DEFAULT nextval('public.execution_variables_id_seq'::regclass);


--
-- Name: requirements_ai_configs id; Type: DEFAULT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.requirements_ai_configs ALTER COLUMN id SET DEFAULT nextval('public.requirements_ai_configs_id_seq'::regclass);


--
-- Name: requirements_messages id; Type: DEFAULT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.requirements_messages ALTER COLUMN id SET DEFAULT nextval('public.requirements_messages_id_seq'::regclass);


--
-- Name: step_executions id; Type: DEFAULT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.step_executions ALTER COLUMN id SET DEFAULT nextval('public.step_executions_id_seq'::regclass);


--
-- Name: templates id; Type: DEFAULT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.templates ALTER COLUMN id SET DEFAULT nextval('public.templates_id_seq'::regclass);


--
-- Name: test_cases id; Type: DEFAULT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.test_cases ALTER COLUMN id SET DEFAULT nextval('public.test_cases_id_seq'::regclass);


--
-- Name: variable_references id; Type: DEFAULT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.variable_references ALTER COLUMN id SET DEFAULT nextval('public.variable_references_id_seq'::regclass);


--
-- Data for Name: execution_history; Type: TABLE DATA; Schema: public; Owner: intent_user
--

COPY public.execution_history (id, execution_id, test_case_id, status, mode, browser, start_time, end_time, duration, steps_total, steps_passed, steps_failed, result_summary, screenshots_path, logs_path, error_message, error_stack, executed_by, created_at) FROM stdin;
\.


--
-- Data for Name: execution_variables; Type: TABLE DATA; Schema: public; Owner: intent_user
--

COPY public.execution_variables (id, execution_id, variable_name, variable_value, data_type, source_step_index, source_api_method, source_api_params, created_at, is_encrypted) FROM stdin;
\.


--
-- Data for Name: requirements_ai_configs; Type: TABLE DATA; Schema: public; Owner: intent_user
--

COPY public.requirements_ai_configs (id, config_name, api_key, base_url, model_name, is_default, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: requirements_messages; Type: TABLE DATA; Schema: public; Owner: intent_user
--

COPY public.requirements_messages (id, session_id, message_type, content, message_metadata, attached_files, created_at) FROM stdin;
\.


--
-- Data for Name: requirements_sessions; Type: TABLE DATA; Schema: public; Owner: intent_user
--

COPY public.requirements_sessions (id, project_name, session_status, current_stage, user_context, ai_context, consensus_content, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: step_executions; Type: TABLE DATA; Schema: public; Owner: intent_user
--

COPY public.step_executions (id, execution_id, step_index, step_description, status, start_time, end_time, duration, screenshot_path, ai_confidence, ai_decision, error_message) FROM stdin;
\.


--
-- Data for Name: templates; Type: TABLE DATA; Schema: public; Owner: intent_user
--

COPY public.templates (id, name, description, category, steps_template, parameters, usage_count, created_by, created_at, is_public) FROM stdin;
\.


--
-- Data for Name: test_cases; Type: TABLE DATA; Schema: public; Owner: intent_user
--

COPY public.test_cases (id, name, description, steps, tags, category, priority, created_by, created_at, updated_at, is_active) FROM stdin;
\.


--
-- Data for Name: variable_references; Type: TABLE DATA; Schema: public; Owner: intent_user
--

COPY public.variable_references (id, execution_id, step_index, variable_name, reference_path, parameter_name, original_expression, resolved_value, resolution_status, error_message, created_at) FROM stdin;
\.


--
-- Name: execution_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: intent_user
--

SELECT pg_catalog.setval('public.execution_history_id_seq', 1, false);


--
-- Name: execution_variables_id_seq; Type: SEQUENCE SET; Schema: public; Owner: intent_user
--

SELECT pg_catalog.setval('public.execution_variables_id_seq', 1, false);


--
-- Name: requirements_ai_configs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: intent_user
--

SELECT pg_catalog.setval('public.requirements_ai_configs_id_seq', 1, false);


--
-- Name: requirements_messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: intent_user
--

SELECT pg_catalog.setval('public.requirements_messages_id_seq', 1, false);


--
-- Name: step_executions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: intent_user
--

SELECT pg_catalog.setval('public.step_executions_id_seq', 1, false);


--
-- Name: templates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: intent_user
--

SELECT pg_catalog.setval('public.templates_id_seq', 1, false);


--
-- Name: test_cases_id_seq; Type: SEQUENCE SET; Schema: public; Owner: intent_user
--

SELECT pg_catalog.setval('public.test_cases_id_seq', 1, false);


--
-- Name: variable_references_id_seq; Type: SEQUENCE SET; Schema: public; Owner: intent_user
--

SELECT pg_catalog.setval('public.variable_references_id_seq', 1, false);


--
-- Name: execution_history execution_history_execution_id_key; Type: CONSTRAINT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.execution_history
    ADD CONSTRAINT execution_history_execution_id_key UNIQUE (execution_id);


--
-- Name: execution_history execution_history_pkey; Type: CONSTRAINT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.execution_history
    ADD CONSTRAINT execution_history_pkey PRIMARY KEY (id);


--
-- Name: execution_variables execution_variables_pkey; Type: CONSTRAINT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.execution_variables
    ADD CONSTRAINT execution_variables_pkey PRIMARY KEY (id);


--
-- Name: requirements_ai_configs requirements_ai_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.requirements_ai_configs
    ADD CONSTRAINT requirements_ai_configs_pkey PRIMARY KEY (id);


--
-- Name: requirements_messages requirements_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.requirements_messages
    ADD CONSTRAINT requirements_messages_pkey PRIMARY KEY (id);


--
-- Name: requirements_sessions requirements_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.requirements_sessions
    ADD CONSTRAINT requirements_sessions_pkey PRIMARY KEY (id);


--
-- Name: step_executions step_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.step_executions
    ADD CONSTRAINT step_executions_pkey PRIMARY KEY (id);


--
-- Name: templates templates_pkey; Type: CONSTRAINT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.templates
    ADD CONSTRAINT templates_pkey PRIMARY KEY (id);


--
-- Name: test_cases test_cases_pkey; Type: CONSTRAINT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.test_cases
    ADD CONSTRAINT test_cases_pkey PRIMARY KEY (id);


--
-- Name: execution_variables uk_execution_variable_name; Type: CONSTRAINT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.execution_variables
    ADD CONSTRAINT uk_execution_variable_name UNIQUE (execution_id, variable_name);


--
-- Name: variable_references variable_references_pkey; Type: CONSTRAINT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.variable_references
    ADD CONSTRAINT variable_references_pkey PRIMARY KEY (id);


--
-- Name: idx_execution_created_at; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_execution_created_at ON public.execution_history USING btree (created_at);


--
-- Name: idx_execution_executed_by; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_execution_executed_by ON public.execution_history USING btree (executed_by);


--
-- Name: idx_execution_start_time; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_execution_start_time ON public.execution_history USING btree (start_time);


--
-- Name: idx_execution_status; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_execution_status ON public.execution_history USING btree (status);


--
-- Name: idx_execution_step; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_execution_step ON public.execution_variables USING btree (execution_id, source_step_index);


--
-- Name: idx_execution_testcase_status; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_execution_testcase_status ON public.execution_history USING btree (test_case_id, status);


--
-- Name: idx_execution_variable; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_execution_variable ON public.execution_variables USING btree (execution_id, variable_name);


--
-- Name: idx_reference_execution_step; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_reference_execution_step ON public.variable_references USING btree (execution_id, step_index);


--
-- Name: idx_reference_status; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_reference_status ON public.variable_references USING btree (execution_id, resolution_status);


--
-- Name: idx_reference_variable; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_reference_variable ON public.variable_references USING btree (execution_id, variable_name);


--
-- Name: idx_requirements_message_created; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_requirements_message_created ON public.requirements_messages USING btree (created_at);


--
-- Name: idx_requirements_message_session; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_requirements_message_session ON public.requirements_messages USING btree (session_id, created_at);


--
-- Name: idx_requirements_message_type; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_requirements_message_type ON public.requirements_messages USING btree (session_id, message_type);


--
-- Name: idx_requirements_session_created; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_requirements_session_created ON public.requirements_sessions USING btree (created_at);


--
-- Name: idx_requirements_session_stage; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_requirements_session_stage ON public.requirements_sessions USING btree (current_stage);


--
-- Name: idx_requirements_session_status; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_requirements_session_status ON public.requirements_sessions USING btree (session_status);


--
-- Name: idx_requirements_session_updated; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_requirements_session_updated ON public.requirements_sessions USING btree (updated_at);


--
-- Name: idx_step_execution_id_index; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_step_execution_id_index ON public.step_executions USING btree (execution_id, step_index);


--
-- Name: idx_step_start_time; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_step_start_time ON public.step_executions USING btree (start_time);


--
-- Name: idx_step_status; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_step_status ON public.step_executions USING btree (execution_id, status);


--
-- Name: idx_testcase_active; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_testcase_active ON public.test_cases USING btree (is_active);


--
-- Name: idx_testcase_category; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_testcase_category ON public.test_cases USING btree (category, is_active);


--
-- Name: idx_testcase_created; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_testcase_created ON public.test_cases USING btree (created_at);


--
-- Name: idx_testcase_priority; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_testcase_priority ON public.test_cases USING btree (priority, is_active);


--
-- Name: idx_variable_type; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX idx_variable_type ON public.execution_variables USING btree (execution_id, data_type);


--
-- Name: ix_requirements_messages_session_id; Type: INDEX; Schema: public; Owner: intent_user
--

CREATE INDEX ix_requirements_messages_session_id ON public.requirements_messages USING btree (session_id);


--
-- Name: execution_history execution_history_test_case_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.execution_history
    ADD CONSTRAINT execution_history_test_case_id_fkey FOREIGN KEY (test_case_id) REFERENCES public.test_cases(id);


--
-- Name: execution_variables execution_variables_execution_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.execution_variables
    ADD CONSTRAINT execution_variables_execution_id_fkey FOREIGN KEY (execution_id) REFERENCES public.execution_history(execution_id);


--
-- Name: requirements_messages requirements_messages_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.requirements_messages
    ADD CONSTRAINT requirements_messages_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.requirements_sessions(id);


--
-- Name: step_executions step_executions_execution_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.step_executions
    ADD CONSTRAINT step_executions_execution_id_fkey FOREIGN KEY (execution_id) REFERENCES public.execution_history(execution_id);


--
-- Name: variable_references variable_references_execution_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: intent_user
--

ALTER TABLE ONLY public.variable_references
    ADD CONSTRAINT variable_references_execution_id_fkey FOREIGN KEY (execution_id) REFERENCES public.execution_history(execution_id);


--
-- PostgreSQL database dump complete
--

\unrestrict RBOY5p7mBC8YdKEguhaKa5PSjhpnCRdW03I3wX0fKJaWu7hhgOB4ptOzPclkzRs

