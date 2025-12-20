'use client';
import {
  Box,
  VStack,
  HStack,
  Text,
  Heading,
  Button,
  Radio,
  RadioGroup,
  Input,
  Badge,
  useToast
} from '@chakra-ui/react';
import { useState, useEffect } from 'react';
import { api } from '@/services/api';
import { useGraph } from '@/contexts/GraphContext';

interface QuizQuestion {
  type: 'multiple_choice' | 'true_false' | 'short_answer';
  question: string;
  options?: string[];
  correct_answer: string;
  explanation: string;
  concept_id: string;
}

export function QuizInterface() {
  const { graph } = useGraph();
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [showResults, setShowResults] = useState(false);
  const [score, setScore] = useState(0);
  const toast = useToast();
  
  useEffect(() => {
    generateQuiz();
  }, [graph]);
  
  const generateQuiz = async () => {
    try {
      // Extract concepts from graph
      const concepts = graph?.nodes?.map(node => ({
        id: node.id,
        name: node.data?.name || 'Unknown',
        description: node.data?.description || ''
      })) || [];
      
      if (concepts.length === 0) {
        toast({
          title: 'No concepts available',
          description: 'Complete a study query first to generate a quiz',
          status: 'warning',
          duration: 3000
        });
        return;
      }
      
      // Call quiz generation API (would need to be implemented)
      // For now, use mock questions
      const mockQuestions: QuizQuestion[] = concepts.slice(0, 5).map((concept, idx) => ({
        type: 'multiple_choice',
        question: `What is ${concept.name}?`,
        options: [
          concept.description.substring(0, 50) || 'Option 1',
          'Option 2',
          'Option 3',
          'Option 4'
        ],
        correct_answer: concept.description.substring(0, 50) || 'Option 1',
        explanation: `See ${concept.name} for details.`,
        concept_id: concept.id
      }));
      
      setQuestions(mockQuestions);
      setCurrentQuestion(0);
      setAnswers({});
      setShowResults(false);
      setScore(0);
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to generate quiz',
        status: 'error',
        duration: 5000
      });
    }
  };
  
  const handleAnswer = (answer: string) => {
    setAnswers(prev => ({ ...prev, [currentQuestion]: answer }));
  };
  
  const handleNext = () => {
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(prev => prev + 1);
    } else {
      calculateScore();
      setShowResults(true);
    }
  };
  
  const handlePrevious = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion(prev => prev - 1);
    }
  };
  
  const calculateScore = () => {
    let correct = 0;
    questions.forEach((q, idx) => {
      if (answers[idx] === q.correct_answer) {
        correct++;
      }
    });
    setScore(correct);
  };
  
  if (questions.length === 0) {
    return (
      <Box p={4} bg="white" borderRight="1px" borderColor="gray.200">
        <VStack spacing={4}>
          <Text fontSize="sm" color="gray.500">
            No quiz available. Complete a study query to generate questions.
          </Text>
          <Button size="sm" colorScheme="blue" onClick={generateQuiz}>
            Generate Quiz
          </Button>
        </VStack>
      </Box>
    );
  }
  
  const question = questions[currentQuestion];
  const userAnswer = answers[currentQuestion];
  const isCorrect = showResults && userAnswer === question.correct_answer;
  
  return (
    <Box
      w="100%"
      h="100vh"
      overflowY="auto"
      p={4}
      bg="white"
    >
      <Heading size="sm" mb={4}>
        Quiz
        {showResults && (
          <Badge ml={2} colorScheme={score >= questions.length / 2 ? 'green' : 'red'}>
            {score}/{questions.length}
          </Badge>
        )}
      </Heading>
      
      {!showResults ? (
        <VStack align="stretch" spacing={4}>
          {/* Question Progress */}
          <Text fontSize="xs" color="gray.500">
            Question {currentQuestion + 1} of {questions.length}
          </Text>
          
          {/* Question */}
          <Text fontSize="md" fontWeight="medium">
            {question.question}
          </Text>
          
          {/* Answer Options */}
          {question.type === 'multiple_choice' && question.options && (
            <RadioGroup
              value={userAnswer || ''}
              onChange={handleAnswer}
            >
              <VStack align="stretch" spacing={2}>
                {question.options.map((option, idx) => (
                  <Radio key={idx} value={option}>
                    {option}
                  </Radio>
                ))}
              </VStack>
            </RadioGroup>
          )}
          
          {question.type === 'true_false' && (
            <RadioGroup value={userAnswer || ''} onChange={handleAnswer}>
              <VStack align="stretch" spacing={2}>
                <Radio value="true">True</Radio>
                <Radio value="false">False</Radio>
              </VStack>
            </RadioGroup>
          )}
          
          {question.type === 'short_answer' && (
            <Input
              value={userAnswer || ''}
              onChange={(e) => handleAnswer(e.target.value)}
              placeholder="Your answer..."
            />
          )}
          
          {/* Navigation */}
          <HStack spacing={2} mt={4}>
            <Button
              size="sm"
              variant="outline"
              onClick={handlePrevious}
              isDisabled={currentQuestion === 0}
            >
              Previous
            </Button>
            <Button
              size="sm"
              colorScheme="blue"
              onClick={handleNext}
              isDisabled={!userAnswer}
            >
              {currentQuestion === questions.length - 1 ? 'Finish' : 'Next'}
            </Button>
          </HStack>
        </VStack>
      ) : (
        <VStack align="stretch" spacing={4}>
          <Text fontSize="lg" fontWeight="bold">
            Quiz Complete!
          </Text>
          <Text fontSize="md">
            You scored {score} out of {questions.length}
          </Text>
          
          {/* Review Answers */}
          <VStack align="stretch" spacing={3}>
            {questions.map((q, idx) => (
              <Box key={idx} p={3} bg="gray.50" borderRadius="md">
                <Text fontSize="sm" fontWeight="medium" mb={2}>
                  {q.question}
                </Text>
                <Text fontSize="xs" color="gray.600">
                  Your answer: {answers[idx] || 'No answer'}
                </Text>
                <Text fontSize="xs" color={answers[idx] === q.correct_answer ? 'green.600' : 'red.600'}>
                  Correct answer: {q.correct_answer}
                </Text>
                {q.explanation && (
                  <Text fontSize="xs" color="gray.500" mt={1}>
                    {q.explanation}
                  </Text>
                )}
              </Box>
            ))}
          </VStack>
          
          <Button size="sm" colorScheme="blue" onClick={generateQuiz}>
            Retake Quiz
          </Button>
        </VStack>
      )}
    </Box>
  );
}
