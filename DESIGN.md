# DESIGN

이 문서는 so2x-flow scaffold 자체의 설계 원칙이 아니라, 타깃 프로젝트에 덧씌우는 UI/UX 기준선이다.
즉, harness 구조나 runner 정책을 만질 때 이 파일부터 붙잡고 씨름할 필요는 없다.

## Usage
- 타깃 프로젝트에 별도 디자인 시스템이 없을 때 baseline으로 사용한다.
- so2x-flow scaffold 작업에서는 이 문서를 선택적으로만 참고한다.
- 타깃 프로젝트에 더 강한 디자인 시스템이 있으면 그쪽이 우선이다.

## Design Intent
- Keep the interface calm, direct, and easy to scan.
- Prefer obvious hierarchy over decorative variety.
- Make primary actions and state changes immediately understandable.

## Color
- Use one primary accent for main actions.
- Keep neutrals dominant for layout and body surfaces.
- Reserve destructive color only for destructive actions.
- Avoid mixing multiple competing accents in the same view.

## Spacing
- Use a predictable spacing scale.
- Prefer generous spacing between sections over dense packing.
- Keep related controls visually grouped.

## Typography and Tone
- Favor simple, readable type scales.
- Keep labels explicit and short.
- Avoid vague CTA labels like "Continue" when a more specific action is possible.

## Component Rules
- Forms should show field grouping and validation state clearly.
- Tables and lists should prioritize scanability over density.
- Empty states should explain what to do next.
- Status indicators should be visible without opening secondary panels.

## Anti-patterns
- Too many competing primary buttons.
- Low-contrast text.
- Hidden state changes without feedback.
- Inconsistent spacing between similar components.
- Decorative UI that weakens task clarity.
