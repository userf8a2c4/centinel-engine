// EN: Header component with navigation tabs, dark mode toggle, language, accessibility menu
// ES: Componente de encabezado con pestañas, toggle de modo oscuro, idioma, menú de accesibilidad

import { useState, useRef, useEffect } from 'react';
import {
  Sun,
  Moon,
  Globe,
  Eye,
  ExternalLink,
  ChevronDown,
  Shield,
} from 'lucide-react';
import type { TabId, AccessibilityMode, Language } from '../types/election';
import { t } from '../data/i18n';

interface HeaderProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  theme: 'light' | 'dark';
  onThemeToggle: () => void;
  language: Language;
  onLanguageChange: (lang: Language) => void;
  accessibilityMode: AccessibilityMode;
  onAccessibilityChange: (mode: AccessibilityMode) => void;
}

export default function Header({
  activeTab,
  onTabChange,
  theme,
  onThemeToggle,
  language,
  onLanguageChange,
  accessibilityMode,
  onAccessibilityChange,
}: HeaderProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // EN: Close menu on outside click
  // ES: Cerrar menú al hacer click fuera
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const tabs: TabId[] = ['ciudadano', 'auditor', 'ethos'];

  const accessibilityOptions: { value: AccessibilityMode; labelKey: 'none' | 'protanopia' | 'deuteranopia' | 'tritanopia' | 'highContrast' }[] = [
    { value: 'none', labelKey: 'none' },
    { value: 'protanopia', labelKey: 'protanopia' },
    { value: 'deuteranopia', labelKey: 'deuteranopia' },
    { value: 'tritanopia', labelKey: 'tritanopia' },
    { value: 'high-contrast', labelKey: 'highContrast' },
  ];

  return (
    <header
      className="sticky top-0 z-50 glass bg-white/80 dark:bg-slate-900/80 border-b border-gray-200/50 dark:border-gray-700/50"
      role="banner"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
        {/* EN: Logo / ES: Logo */}
        <div className="flex items-center gap-2 shrink-0">
          <Shield className="w-6 h-6 text-brand" aria-hidden="true" />
          <span className="text-lg font-bold tracking-wider text-brand select-none">
            CENTINEL
          </span>
        </div>

        {/* EN: Navigation tabs / ES: Pestañas de navegación */}
        <nav
          className="flex items-center gap-1 bg-gray-100/80 dark:bg-slate-800/80 rounded-2xl p-1"
          role="tablist"
          aria-label="Dashboard navigation"
        >
          {tabs.map((tab) => (
            <button
              key={tab}
              role="tab"
              aria-selected={activeTab === tab}
              onClick={() => onTabChange(tab)}
              className={`px-4 py-1.5 rounded-xl text-sm font-semibold uppercase tracking-wide transition-all duration-200 ${
                activeTab === tab
                  ? 'bg-white dark:bg-slate-700 text-brand shadow-sm'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
              }`}
            >
              {t(language, tab)}
            </button>
          ))}
        </nav>

        {/* EN: Settings menu / ES: Menú de ajustes */}
        <div className="relative shrink-0" ref={menuRef}>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors"
            aria-expanded={menuOpen}
            aria-haspopup="true"
            aria-label="Settings menu"
          >
            <Eye className="w-4 h-4" aria-hidden="true" />
            <ChevronDown className="w-3 h-3" aria-hidden="true" />
          </button>

          {menuOpen && (
            <div
              className="absolute right-0 top-full mt-2 w-64 glass bg-white/90 dark:bg-slate-800/90 border border-gray-200/60 dark:border-gray-700/60 rounded-2xl shadow-xl p-3 space-y-3"
              role="menu"
            >
              {/* EN: Theme toggle / ES: Toggle de tema */}
              <button
                onClick={onThemeToggle}
                className="flex items-center gap-3 w-full px-3 py-2 rounded-xl hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors text-sm text-gray-700 dark:text-gray-200"
                role="menuitem"
              >
                {theme === 'dark' ? (
                  <Sun className="w-4 h-4 text-amber-400" aria-hidden="true" />
                ) : (
                  <Moon className="w-4 h-4 text-indigo-500" aria-hidden="true" />
                )}
                {theme === 'dark' ? t(language, 'lightMode') : t(language, 'darkMode')}
              </button>

              {/* EN: Language toggle / ES: Toggle de idioma */}
              <div className="px-3 py-2">
                <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 mb-2">
                  <Globe className="w-3.5 h-3.5" aria-hidden="true" />
                  {t(language, 'language')}
                </div>
                <div className="flex gap-2">
                  {(['es', 'en'] as Language[]).map((lang) => (
                    <button
                      key={lang}
                      onClick={() => onLanguageChange(lang)}
                      className={`px-3 py-1 rounded-lg text-xs font-semibold uppercase transition-colors ${
                        language === lang
                          ? 'bg-brand text-white'
                          : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600'
                      }`}
                      role="menuitemradio"
                      aria-checked={language === lang}
                    >
                      {lang}
                    </button>
                  ))}
                </div>
              </div>

              {/* EN: Accessibility mode / ES: Modo de accesibilidad */}
              <div className="px-3 py-2">
                <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 mb-2">
                  <Eye className="w-3.5 h-3.5" aria-hidden="true" />
                  {t(language, 'accessibility')}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {accessibilityOptions.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => onAccessibilityChange(opt.value)}
                      className={`px-2 py-1 rounded-lg text-xs font-medium transition-colors ${
                        accessibilityMode === opt.value
                          ? 'bg-brand text-white'
                          : 'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600'
                      }`}
                      role="menuitemradio"
                      aria-checked={accessibilityMode === opt.value}
                    >
                      {t(language, opt.labelKey)}
                    </button>
                  ))}
                </div>
              </div>

              {/* EN: GitHub link / ES: Enlace a GitHub */}
              <a
                href="https://github.com/userf8c4/centinel-engine"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors text-sm text-gray-700 dark:text-gray-200"
                role="menuitem"
              >
                <ExternalLink className="w-4 h-4" aria-hidden="true" />
                {t(language, 'github')}
              </a>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
