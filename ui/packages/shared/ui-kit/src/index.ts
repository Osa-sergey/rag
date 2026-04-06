/* ═══════════════════════════════════════════
   @ui/ui-kit — Shared Design System
   ═══════════════════════════════════════════ */

// Components
export { Badge } from "./Badge";
export type { BadgeProps, BadgeVariant, BadgeSize } from "./Badge";

export { StatusIcon } from "./StatusIcon";
export type { StatusIconProps, Status } from "./StatusIcon";

export { Tooltip } from "./Tooltip";
export type { TooltipProps, TooltipPosition } from "./Tooltip";

export { Skeleton } from "./Skeleton";
export type { SkeletonProps, SkeletonVariant } from "./Skeleton";

export { Panel } from "./Panel";
export type { PanelProps, PanelSide } from "./Panel";

export { SearchBar } from "./SearchBar";
export type { SearchBarProps } from "./SearchBar";

export { TabPanel } from "./TabPanel";
export type { TabPanelProps, Tab } from "./TabPanel";

export { Accordion } from "./Accordion";
export type { AccordionProps, AccordionItem } from "./Accordion";

export { KeyValueList } from "./KeyValueList";
export type { KeyValueListProps, KeyValueEntry } from "./KeyValueList";

export { DataTable } from "./DataTable";
export type { DataTableProps, Column } from "./DataTable";

export { Input } from "./Input";
export type { InputProps, InputVariant, InputSize } from "./Input";

export { Toggle } from "./Toggle";
export type { ToggleProps, ToggleVariant } from "./Toggle";

export { Toast } from "./Toast";
export type { ToastProps, ToastVariant } from "./Toast";

export { ProgressBar } from "./ProgressBar";
export type { ProgressBarProps } from "./ProgressBar";

export { EmptyState } from "./EmptyState";
export type { EmptyStateProps, EmptyStateType } from "./EmptyState";

export { FilterChips } from "./FilterChips";
export type { FilterChipsProps, Chip } from "./FilterChips";

export { Checkbox } from "./Checkbox";
export type { CheckboxProps } from "./Checkbox";

export { Slider } from "./Slider";
export type { SliderProps } from "./Slider";

export { Breadcrumb } from "./Breadcrumb";
export type { BreadcrumbProps, BreadcrumbItem } from "./Breadcrumb";

export { ViewSwitcher } from "./ViewSwitcher";
export type { ViewSwitcherProps, ViewOption } from "./ViewSwitcher";

export { Timeline } from "./Timeline";
export type { TimelineProps, TimelineItem } from "./Timeline";

export { Select } from "./Select";
export type { SelectProps, SelectOption } from "./Select";

export { Modal } from "./Modal";
export type { ModalProps, ModalSize } from "./Modal";

export { ConfirmDialog } from "./ConfirmDialog";
export type { ConfirmDialogProps, ConfirmDialogIntent } from "./ConfirmDialog";

export { AlertBanner } from "./AlertBanner";
export type { AlertBannerProps, AlertBannerVariant } from "./AlertBanner";

export { Popover } from "./Popover";
export type { PopoverProps, PopoverTrigger, PopoverPlacement } from "./Popover";

export { Drawer } from "./Drawer";
export type { DrawerProps, DrawerSide, DrawerSize } from "./Drawer";

export { TopBar } from "./TopBar";
export type { TopBarProps } from "./TopBar";

export { DiffViewer } from "./DiffViewer";
export type { DiffViewerProps, DiffViewMode, DiffLine } from "./DiffViewer";

export { MarkdownRenderer } from "./MarkdownRenderer";
export type { MarkdownRendererProps, HighlightSpan } from "./MarkdownRenderer";

export { SourceTextViewer } from "./SourceTextViewer";
export type { SourceTextViewerProps, SourceTextTab } from "./SourceTextViewer";

export { CodeEditor } from "./CodeEditor";
export type { CodeEditorProps, CodeEditorError, CodeLanguage } from "./CodeEditor";

export { JsonSchemaForm } from "./JsonSchemaForm";
export type { JsonSchemaFormProps, SchemaField, FieldSource } from "./JsonSchemaForm";

export { ColorPicker } from "./ColorPicker";
export type { ColorPickerProps } from "./ColorPicker";

export { IconPicker } from "./IconPicker";
export type { IconPickerProps } from "./IconPicker";

// React Flow Layer
export { FlowCanvas } from "./FlowCanvas";
export type { FlowCanvasProps, FlowNode, FlowEdge } from "./FlowCanvas";

export { FilterPanel } from "./FilterPanel";
export type { FilterPanelProps, FilterGroup, SliderFilter } from "./FilterPanel";

export { NodeTooltip } from "./NodeTooltip";
export type { NodeTooltipProps } from "./NodeTooltip";

export { EdgeLabel } from "./EdgeLabel";
export type { EdgeLabelProps, EdgeLabelVariant } from "./EdgeLabel";

export { GroupNode } from "./GroupNode";
export type { GroupNodeProps } from "./GroupNode";

// DAG Builder Domain Components
export { StepNode } from "./StepNode";
export type { StepNodeProps, StepStatus, StepNodePort, CallbackInfo, ContextInfo } from "./StepNode";

export { DataEdge } from "./DataEdge";
export type { DataEdgeProps } from "./DataEdge";

// DAG Builder specific panels
export * from "./NodePalette";
export * from "./PipelineToolbar";
export * from "./ValidationOverlay";
export * from "./InspectorPanel";
export * from "./YamlPanel";
export * from "./ConfigForm";
export * from "./HydraDefaultsSelector";
export * from "./CallbackPicker";

export * from "./ContextInspector";

// Knowledge Base Domain Components
export { ConceptCard } from "./ConceptCard";
export type { ConceptCardProps } from "./ConceptCard";

export { ArticleCard } from "./ArticleCard";
export type { ArticleCardProps } from "./ArticleCard";

export { KBNode } from "./KBNode";
export type { KBNodeProps, KBNodeType } from "./KBNode";

export { NavigatorSidebar } from "./NavigatorSidebar";
export type { NavigatorSidebarProps, NavigatorItem, NavigatorTab } from "./NavigatorSidebar";

export { ConceptDetailPanel } from "./ConceptDetailPanel";
export type { ConceptDetailPanelProps, ConceptDetailVersion, ConceptDetailSource } from "./ConceptDetailPanel";

export { KeywordDetailPanel } from "./KeywordDetailPanel/KeywordDetailPanel";
export type { KeywordDetailPanelProps, KeywordOccurrence } from "./KeywordDetailPanel/KeywordDetailPanel";

export { ArticleDetailPanel } from "./ArticleDetailPanel/ArticleDetailPanel";
export type { ArticleDetailPanelProps, ArticleKeyword, ArticleChunk } from "./ArticleDetailPanel/ArticleDetailPanel";

export { CreateConceptWizard } from "./CreateConceptWizard/CreateConceptWizard";
export type { CreateConceptWizardProps } from "./CreateConceptWizard/CreateConceptWizard";

export { KeywordReviewList } from "./KeywordReviewList/KeywordReviewList";
export type { KeywordReviewListProps, ReviewKeyword } from "./KeywordReviewList/KeywordReviewList";

export { VersionTimeline } from "./VersionTimeline";
export type { VersionTimelineProps, ConceptVersion, ConceptChange } from "./VersionTimeline";

export { ArticlePoolSelector } from "./ArticlePoolSelector";
export type { ArticlePoolSelectorProps } from "./ArticlePoolSelector";

// DAG Builder — Panels
export { InspectorPanel } from "./InspectorPanel";
export type { InspectorPanelProps, InspectorTab, InspectorField } from "./InspectorPanel";

export { YamlPanel } from "./YamlPanel";
export type { YamlPanelProps } from "./YamlPanel";

// Knowledge Base — Panels
export { RaptorTreeView } from "./RaptorTreeView";
export type { RaptorTreeViewProps, TreeNode } from "./RaptorTreeView";

export { ExpandPanel } from "./ExpandPanel";
export type { ExpandPanelProps, DiffLine as ExpandDiffLine } from "./ExpandPanel";

export { InboxPanel } from "./InboxPanel";
export type { InboxPanelProps, InboxItem } from "./InboxPanel";

export { GlossaryTable } from "./GlossaryTable";
export type { GlossaryTableProps, GlossaryEntry } from "./GlossaryTable";

// AppShell
export { AppShell } from "./AppShell";
export type { AppShellProps } from "./AppShell";

// Base — RangeInput
export { RangeInput } from "./RangeInput";
export type { RangeInputProps } from "./RangeInput";

// Combined Pickers
export { IconColorPicker } from "./IconColorPicker";
export type { IconColorPickerProps } from "./IconColorPicker";

// Motion presets
export * from "./motion";
